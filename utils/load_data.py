import json
import sys
from pathlib import Path
from sqlmodel import Session, select
from app.models import Tag, Document
from app.main import engine, create_db_and_tables


def load_data(json_file: Path):
    """
    Load documents and tags from a JSON file into the database.
    Expected JSON format:
    {
        "tags": {
            "python": "Python programming language",
            "fastapi": "FastAPI web framework",
            ...
        },
        "documents": [
            {
                "title": "Document Title",
                "description": "Document Description",
                "content": "Full document content...",
                "tags": ["python", "fastapi"]
            },
            ...
        ]
    }
    """
    # Create tables if they don't exist
    create_db_and_tables()

    with Session(engine) as session:
        # Load JSON data
        with open(json_file) as f:
            data = json.load(f)

        # Create tags first
        tag_map = {}  # Map tag names to Tag objects
        for tag_name, description in data["tags"].items():
            # Check if tag already exists
            existing_tag = session.exec(
                select(Tag).where(Tag.name == tag_name)
            ).first()
            
            if existing_tag:
                tag_map[tag_name] = existing_tag
            else:
                tag = Tag(name=tag_name, description=description)
                session.add(tag)
                session.commit()
                session.refresh(tag)
                tag_map[tag_name] = tag

        # Create documents
        for doc_data in data["documents"]:
            # Get Tag objects for this document
            doc_tags = [tag_map[tag_name] for tag_name in doc_data["tags"]]
            
            # Create document
            document = Document(
                title=doc_data["title"],
                description=doc_data["description"],
                content=doc_data["content"],
                tags=doc_tags
            )
            session.add(document)
        
        session.commit()


def main():
    if len(sys.argv) != 2:
        print("Usage: python -m utils.load_data <json_file>")
        sys.exit(1)
    
    json_file = Path(sys.argv[1])
    if not json_file.exists():
        print(f"Error: File {json_file} does not exist")
        sys.exit(1)

    load_data(json_file)
    print("Data loaded successfully!")


if __name__ == "__main__":
    main()
