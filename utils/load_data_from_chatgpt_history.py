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
import llm

model = llm.get_model("gpt-4o-mini")


def score_conversation(messages: List[str], title: str) -> bool:
    """
    Determine if a conversation is interesting enough to store.
    Criteria:
    - At least 3 messages
    - Contains code blocks or technical content
    - Non-trivial conversation length
    """

    content = "\n".join(messages)
    response = model.prompt(
        f"""Score the following text for interestingness on a scale of 0-2, as follows. Just return a number (0, 1 or 2); nothing else

0: Short text defining words, short technical solutions, or playful silly things, or longer text which is mostly programming or code               
2: Extensive text exploring historical, philosophical, or otherwise stimulating or emotional topics in-depth, or shorter text about unusual or intellectual or psychological topics, or things that are like diary entries. Not programming-based things unless they are mostly conceptual.                            
1: Things not fitting into 0 or 2


# Text to score

{content}
"""
    )
    score = response.text()
    assert score in ["0", "1", "2"]
    return int(score)


def tag_conversation(messages: List[str], title: str) -> bool:

    content = "\n".join(messages)
    # Fetch existing tags from database
    with Session(engine) as session:
        tags = session.exec(select(Tag)).all()
        existing_tags = json.dumps(
            [{"name": tag.name, "description": tag.description} for tag in tags]
        )
    response = model.prompt(
        f"""Return an array of json tags that categories the following text.

        Consider existing tags first, and prefer these if they are appropriate.

        If none of them fit, or some fit but some new ones would be suitable, then invent new tags as necessary.

        Example: [{"name": "programming", "description": "Computer Programming"}]

        Existing tags: {existing_tags}


# Text to tag

{content}
"""
    )
    result = response.text()
    return result


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

            def extract_message_parts(message):
                """Extract the text parts from a message content."""
                content = message.get("content")
                if content and content.get("content_type") == "text":
                    return content.get("parts", [])
                return []

            def get_author_name(message):
                """Get the author name from a message."""
                author = message.get("author", {}).get("role", "")
                if author == "assistant":
                    return "ChatGPT"
                elif author == "system":
                    return "System"
                return author

            def get_conversation_messages(conversation):
                """Extract messages from a conversation in chronological order."""
                messages = []
                current_node = conversation.get("current_node")
                mapping = conversation.get("mapping", {})

                while current_node:
                    node = mapping.get(current_node, {})
                    message = node.get("message") if node else None
                    if message:
                        parts = extract_message_parts(message)
                        author = get_author_name(message)
                        if parts and len(parts) > 0 and len(parts[0]) > 0:
                            if author != "system" or message.get("metadata", {}).get(
                                "is_user_system_message"
                            ):
                                messages.append(f"{author}: {parts[0]}")
                    current_node = node.get("parent") if node else None

                return messages[::-1]  # Reverse to get chronological order

            # Extract messages using the new function
            messages = get_conversation_messages(conv_data)

            # Combine messages into content
            content = "\n\n".join(messages)

            # Only store interesting conversations
            interestingness = score_conversation(messages, title)
            print(f"Processing interesting conversation: {title}")
            if interestingness > 0:
                tags = tag_conversation(messages, title)
            else:
                tags = []

            # XXX add tag creation here -- only create tags that don't already exist
            # Parse create time
            create_time = conv_data.get("create_time", 0)
            created_at = (
                datetime.fromtimestamp(create_time)
                if create_time
                else datetime.utcnow()
            )

            # Create document directly in database
            with Session(engine) as session:
                # XXX also tag the document
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
