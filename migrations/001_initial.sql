-- Create the documents table
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    content TEXT NOT NULL,
    tags TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create the FTS5 virtual table
CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
    title,
    description,
    content,
    content='documents',
    content_rowid='id'
);

-- Create triggers to keep FTS index up to date
CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents BEGIN
    INSERT INTO documents_fts(rowid, title, description, content)
    VALUES (new.id, new.title, new.description, new.content);
END;

CREATE TRIGGER IF NOT EXISTS documents_ad AFTER DELETE ON documents BEGIN
    INSERT INTO documents_fts(documents_fts, rowid, title, description, content)
    VALUES('delete', old.id, old.title, old.description, old.content);
END;

CREATE TRIGGER IF NOT EXISTS documents_au AFTER UPDATE ON documents BEGIN
    INSERT INTO documents_fts(documents_fts, rowid, title, description, content)
    VALUES('delete', old.id, old.title, old.description, old.content);
    INSERT INTO documents_fts(rowid, title, description, content)
    VALUES (new.id, new.title, new.description, new.content);
END;
