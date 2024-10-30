This is crumpet, an API to allow ChatGPT to save, retrieve, and search documents.

# Searching

When a user asks you to search crumpet, use the search endpoint to help the user identify the most helpful documents, and potentially add them to your context, as follows:

1. Consider what they are asking you to search for and compose a query to help match a reasonable selection of candidates. You can use FST5 query strings. You can use double quotes for exact phrases. You can add an asterisk to the final token for a prefix query. You can use boolean operators NOT, AND and OR. Columns available to you are: title, description, content and tag_data. Full syntax is described below.
2. In particular, consider using tags to filter the results, using an FTS column filter on the tag_data column. Pick suitable tags by checking the tags list endpoint, first,
3. Consider the top 10 results and think carefully about which sound relevant
4. Number the search results and read out a short (max 20 word) description for each result
5. Ask the user which numbers they would like added to your context
6. Add these to the context

# Saving

When a uses asks you to remember or save something to crumpet, first consider any tags available in crumpet already, and suggest these as tags.

If there are no suitable tags, suggest creating new tags, and if the user agrees, then create these tags.

Then save the requested text to crumpet, with the tags, and a suitable short title (max 10 words) and description (max 50 words, preferably less)

## Search syntax

### Full-text Query Syntax

The following block contains a summary of the FTS query syntax in BNF form. A detailed explanation follows.

```
<phrase>    := string [*]
<phrase>    := <phrase> + <phrase>
<neargroup> := NEAR ( <phrase> <phrase> ... [, N] )
<query>     := [ [-] <colspec> :] [^] <phrase>
<query>     := [ [-] <colspec> :] <neargroup>
<query>     := [ [-] <colspec> :] ( <query> )
<query>     := <query> AND <query>
<query>     := <query> OR <query>
<query>     := <query> NOT <query>
<colspec>   := colname
<colspec>   := { colname1 colname2 ... }
```

### FTS5 Strings

Within an FTS expression a string may be specified in one of two ways:

By enclosing it in double quotes ("). Within a string, any embedded double quote characters may be escaped SQL-style - by adding a second double-quote character.

As an FTS5 bareword that is not "AND", "OR" or "NOT" (case sensitive). An FTS5 bareword is a string of one or more consecutive characters that are all either:

Non-ASCII range characters (i.e. unicode codepoints greater than 127), or
One of the 52 upper and lower case ASCII characters, or
One of the 10 decimal digit ASCII characters, or
The underscore character (unicode codepoint 96).
The substitute character (unicode codepoint 26).
Strings that include any other characters must be quoted. Characters that are not currently allowed in barewords, are not quote characters and do not currently serve any special purpose in FTS5 query expressions may at some point in the future be allowed in barewords or used to implement new query functionality. This means that queries that are currently syntax errors because they include such a character outside of a quoted string may be interpreted differently by some future version of FTS5.

### FTS5 Phrases

Each string in an fts5 query is parsed ("tokenized") by the tokenizer and a list of zero or more tokens, or terms, extracted. For example, the default tokenizer tokenizes the string "alpha beta gamma" to three separate tokens - "alpha", "beta" and "gamma" - in that order.

FTS queries are made up of phrases. A phrase is an ordered list of one or more tokens. The tokens from each string in the query each make up a single phrase. Two phrases can be concatenated into a single large phrase using the "+" operator. For example, assuming the tokenizer module being used tokenizes the input "one.two.three" to three separate tokens, the following four queries all specify the same phrase:

... MATCH '"one two three"'
... MATCH 'one + two + three'
... MATCH '"one two" + three'
... MATCH 'one.two.three'
A phrase matches a document if the document contains at least one sub-sequence of tokens that matches the sequence of tokens that make up the phrase.

### FTS5 Prefix Queries

If a "\*" character follows a string within an FTS expression, then the final token extracted from the string is marked as a prefix token. As you might expect, a prefix token matches any document token of which it is a prefix. For example, the first two queries in the following block will match any document that contains the token "one" immediately followed by the token "two" and then any token that begins with "thr".

... MATCH '"one two thr" _ '
... MATCH 'one + two + thr_'
... MATCH '"one two thr*"' -- May not work as expected!
The final query in the block above may not work as expected. Because the "*" character is inside the double-quotes, it will be passed to the tokenizer, which will likely discard it (or perhaps, depending on the specific tokenizer in use, include it as part of the final token) instead of recognizing it as a special FTS character.

### FTS5 Initial Token Queries

If a "^" character appears immediately before a phrase that is not part of a NEAR query, then that phrase only matches a document only if it starts at the first token in a column. The "^" syntax may be combined with a column filter, but may not be inserted into the middle of a phrase.

... MATCH '^one' -- first token in any column must be "one"
... MATCH '^ one + two' -- phrase "one two" must appear at start of a column
... MATCH '^ "one two"' -- same as previous
... MATCH 'a : ^two' -- first token of column "a" must be "two"
... MATCH 'NEAR(^one, two)' -- syntax error!
... MATCH 'one + ^two' -- syntax error!
... MATCH '"^one two"' -- May not work as expected!
3.5. FTS5 NEAR Queries
Two or more phrases may be grouped into a NEAR group. A NEAR group is specified by the token "NEAR" (case sensitive) followed by an open parenthesis character, followed by two or more whitespace separated phrases, optionally followed by a comma and the numeric parameter N, followed by a close parenthesis. For example:

... MATCH 'NEAR("one two" "three four", 10)'
... MATCH 'NEAR("one two" thr\* + four)'
If no N parameter is supplied, it defaults to 10. A NEAR group matches a document if the document contains at least one clump of tokens that:

contains at least one instance of each phrase, and
for which the number of tokens between the end of the first phrase and the beginning of the last phrase in the clump is less than or equal to N.
For example:

CREATE VIRTUAL TABLE ft USING fts5(x);
INSERT INTO ft(rowid, x) VALUES(1, 'A B C D x x x E F x');

... MATCH 'NEAR(e d, 4)'; -- Matches!
... MATCH 'NEAR(e d, 3)'; -- Matches!
... MATCH 'NEAR(e d, 2)'; -- Does not match!

... MATCH 'NEAR("c d" "e f", 3)'; -- Matches!
... MATCH 'NEAR("c" "e f", 3)'; -- Does not match!

... MATCH 'NEAR(a d e, 6)'; -- Matches!
... MATCH 'NEAR(a d e, 5)'; -- Does not match!

... MATCH 'NEAR("a b c d" "b c" "e f", 4)'; -- Matches!
... MATCH 'NEAR("a b c d" "b c" "e f", 3)'; -- Does not match!

### FTS5 Column Filters

A single phrase or NEAR group may be restricted to matching text within a specified column of the FTS table by prefixing it with the column name followed by a colon character. Or to a set of columns by prefixing it with a whitespace separated list of column names enclosed in parenthesis ("curly brackets") followed by a colon character. Column names may be specified using either of the two forms described for strings above. Unlike strings that are part of phrases, column names are not passed to the tokenizer module. Column names are case-insensitive in the usual way for SQLite column names - upper/lower case equivalence is understood for ASCII-range characters only.

... MATCH 'colname : NEAR("one two" "three four", 10)'
... MATCH '"colname" : one + two + three'

... MATCH '{col1 col2} : NEAR("one two" "three four", 10)'
... MATCH '{col2 col1 col3} : one + two + three'
If a column filter specification is preceded by a "-" character, then it is interpreted as a list of column not to match against. For example:

-- Search for matches in all columns except "colname"
... MATCH '- colname : NEAR("one two" "three four", 10)'

-- Search for matches in all columns except "col1", "col2" and "col3"
... MATCH '- {col2 col1 col3} : one + two + three'
Column filter specifications may also be applied to arbitrary expressions enclosed in parenthesis. In this case the column filter applies to all phrases within the expression. Nested column filter operations may only further restrict the subset of columns matched, they can not be used to re-enable filtered columns. For example:

-- The following are equivalent:
... MATCH '{a b} : ( {b c} : "hello" AND "world" )'
... MATCH '(b : "hello") AND ({a b} : "world")'
Finally, a column filter for a single column may be specified by using the column name as the LHS of a MATCH operator (instead of the usual table name). For example:

-- Given the following table
CREATE VIRTUAL TABLE ft USING fts5(a, b, c);

-- The following are equivalent
SELECT _ FROM ft WHERE b MATCH 'uvw AND xyz';
SELECT _ FROM ft WHERE ft MATCH 'b : (uvw AND xyz)';

-- This query cannot match any rows (since all columns are filtered out):
SELECT \* FROM ft WHERE b MATCH 'a : xyz';

Columns available to you are: title, description, content and tag_data

### FTS5 Boolean Operators

Phrases and NEAR groups may be arranged into expressions using boolean operators. In order of precedence, from highest (tightest grouping) to lowest (loosest grouping), the operators are:

Operator Function
<query1> NOT <query2> Matches if query1 matches and query2 does not match.
<query1> AND <query2> Matches if both query1 and query2 match.
<query1> OR <query2> Matches if either query1 or query2 match.
Parenthesis may be used to group expressions in order to modify operator precedence in the usual ways. For example:

-- Because NOT groups more tightly than OR, either of the following may
-- be used to match all documents that contain the token "two" but not
-- "three", or contain the token "one".  
... MATCH 'one OR two NOT three'
... MATCH 'one OR (two NOT three)'

-- Matches documents that contain at least one instance of either "one"
-- or "two", but do not contain any instances of token "three".
... MATCH '(one OR two) NOT three'
Phrases and NEAR groups may also be connected by implicit AND operators. For simplicity, these are not shown in the BNF grammar above. Essentially, any sequence of phrases or NEAR groups (including those restricted to matching specified columns) separated only by whitespace are handled as if there were an implicit AND operator between each pair of phrases or NEAR groups. Implicit AND operators are never inserted after or before an expression enclosed in parenthesis. Implicit AND operators group more tightly than all other operators, including NOT. For example:

... MATCH 'one two three' -- 'one AND two AND three'
... MATCH 'three "one two"' -- 'three AND "one two"'
... MATCH 'NEAR(one two) three' -- 'NEAR(one two) AND three'
... MATCH 'one OR two three' -- 'one OR two AND three'
... MATCH 'one NOT two three' -- 'one NOT (two AND three)'

... MATCH '(one OR two) three' -- Syntax error!
... MATCH 'func(one two)' -- Syntax error!
