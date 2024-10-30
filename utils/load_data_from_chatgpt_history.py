import sys
import json
import zipfile
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import re
from app.models import Document, Tag
from utils.load_data import load_data
from sqlmodel import Session, select
from app.main import engine


def is_interesting_conversation(messages: List[str], title: str) -> bool:
    """
    Determine if a conversation is interesting enough to store.
    Criteria:
    - At least 3 messages
    - Contains code blocks or technical content
    - Non-trivial conversation length
    """
    breakpoint()
    if len(messages) < 3:
        return False

    total_length = sum(len(msg) for msg in messages)
    if total_length < 4:  # Skip very short conversations
        return False

    # Look for technical indicators
    technical_patterns = [
        r"```[a-z]*\n",  # Code blocks
        r"import\s+[a-zA-Z_]",  # Import statements
        r"def\s+[a-zA-Z_]",  # Function definitions
        r"class\s+[a-zA-Z_]",  # Class definitions
        r"git\s+[a-z]+",  # Git commands
        r"docker\s+[a-z]+",  # Docker commands
        r"npm\s+[a-z]+",  # NPM commands
        r"pip\s+[a-z]+",  # Pip commands
    ]

    content = "\n".join(messages)
    for pattern in technical_patterns:
        if re.search(pattern, content):
            return False

    # Check title for technical terms
    technical_terms = ["code", "programming", "thinking"]
    if any(term in title.lower() for term in technical_terms):
        return True

    return False


def extract_conversations(zip_path: Path) -> Dict:
    """
    Extract conversations from ChatGPT export zip file and convert to document format
    """
    documents = []
    tags = {"chatgpt": "Conversation exported from ChatGPT"}

    with zipfile.ZipFile(zip_path) as zf:
        # Find all conversation JSON files
        conv_files = [f for f in zf.namelist() if f.endswith(".json")]

        with zf.open("conversations.json") as f:
            conversations = json.load(f)

        # Handle each conversation in the list
        for conv_data in conversations:
            # Extract title and print it
            title = conv_data.get("title", "Untitled Conversation")
            print(f"Title: {title}")

            # Prepare a flattened message list
            messages = []
            mapping = conv_data.get("mapping", {})
            visited = set()

            def add_message_to_thread(message_id):
                if message_id in visited or message_id not in mapping:
                    return
                visited.add(message_id)

                message_data = mapping[message_id].get("message")
                if message_data:

                    # Extract role and content
                    role = message_data.get("author", {}).get("role", "unknown")
                    content = message_data.get("content", {}).get("parts", [""])[0]
                    if content:
                        breakpoint()
                    else:
                        breakpoint()
                        text = message_data.get("content", {}).get("text", {})
                        content = text.get("content")
                        title = text.get("title")
                        description = text.get("description")
                        print("  extra title", title, description)
                    messages.append(f"{role}: {content}")

                # Recursively add child messages in a depth-first order
                for child_id in mapping[message_id].get("children", []):
                    add_message_to_thread(child_id)

            # Start flattening from root nodes
            for msg_id, msg_content in mapping.items():
                if msg_content.get("parent") is None:  # Identify root messages
                    add_message_to_thread(msg_id)

            # Extract messages using the new function
            messages = get_conversation_messages(conv_data)
            
            # Combine messages into content
            content = "\n\n".join(messages)

            # Only store interesting conversations
            if is_interesting_conversation(messages, title):
                print(f"Processing interesting conversation: {title}")
                
                # Parse create time
                create_time = conv_data.get("create_time", 0)
                created_at = datetime.fromtimestamp(create_time) if create_time else datetime.utcnow()

                # Create document directly in database
                with Session(engine) as session:
                    document = Document(
                        title=title,
                        description="",  # Empty description as requested
                        content=content,
                        created_at=created_at,
                        updated_at=created_at,
                    )
                    session.add(document)
                    session.commit()

    # Return empty dict since we're not using load_data anymore
    return {"tags": {}, "documents": []}


def main():
    if len(sys.argv) != 2:
        print("Usage: python -m utils.load_data_from_chatgpt_history <zip_file>")
        sys.exit(1)

    zip_path = Path(sys.argv[1])
    if not zip_path.exists():
        print(f"Error: File {zip_path} does not exist")
        sys.exit(1)

    if not zipfile.is_zipfile(zip_path):
        print(f"Error: {zip_path} is not a valid zip file")
        sys.exit(1)

    # Process conversations
    extract_conversations(zip_path)
    print("Interesting ChatGPT conversations loaded successfully!")


if __name__ == "__main__":
    main()
