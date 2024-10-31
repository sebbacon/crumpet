This is crumpet, an API to allow ChatGPT to save, retrieve, and search documents.

# Searching

When a user asks you to search crumpet, use the search endpoint to help the user identify the most helpful documents, and potentially add them to your context, as follows:

1. Consider what they are asking you to search for and compose a query to help match a reasonable selection of candidates. You can use FST5 query strings. You can use double quotes for exact phrases. You can add an asterisk to the final token for a prefix query. You can use boolean operators NOT, AND and OR. Columns available to you are: title, description, content and tag_data. Full syntax is described below.
2. In particular, consider using tags to filter the results, using an FTS column filter on the tag_data column. Pick suitable tags by checking the tags list endpoint, first,
3. Consider the top 10 results and think carefully about which sound relevant
4. Number the search results and read out a short (max 20 word) description for each result
5. Ask the user which numbers they would like added to your context
6. Add these to the context

Example search strings:

- "delicious tofu" -- exact phrase search
- delicious tofu -- non-exact
- title:delicious -- delicious must be in the `title` field
- tag:tofu AND (NOT tag:cheese OR NOT title:cheese) -- `tag` field must be tofu, and the `tag` OR `title` field must not be cheese
- tof\* -- matches tofu, tofutti, toffee, etc.

# Saving

When a uses asks you to remember or save something to crumpet,

1. first consider any tags available in crumpet already, and suggest these as tags. Potentially query crumpet for existing tags
2. If there are no suitable tags, sparingly suggest creating new tags, and if the user agrees, then create these tags.
3. Think of a suitable short title (max 10 words) and description (max 50 words, preferably less)
4. Save these and the requested content to crumpet

# Retreiving

When you retrieve a document by its id, add all the information returned to your context.
