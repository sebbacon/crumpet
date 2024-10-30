-- Add interestingness column to document table
ALTER TABLE document ADD COLUMN interestingness INTEGER CHECK (interestingness IN (0, 1, 2) OR interestingness IS NULL);

-- Drop and recreate FTS table to include interestingness
DROP TABLE IF EXISTS documentfts;
CREATE VIRTUAL TABLE documentfts USING fts5(
    title, 
    description, 
    content,
    tag_data,
    interestingness
);

-- Reindex existing documents
INSERT INTO documentfts(rowid, title, description, content, tag_data, interestingness)
SELECT 
    d.id,
    d.title,
    COALESCE(d.description, ''),
    d.content,
    COALESCE(
        (
            SELECT GROUP_CONCAT(t.name || ' ' || COALESCE(t.description, ''), ' ')
            FROM tag t
            JOIN documenttag dt ON dt.tag_id = t.id
            WHERE dt.document_id = d.id
        ),
        ''
    ),
    CAST(d.interestingness AS TEXT)
FROM document d;
