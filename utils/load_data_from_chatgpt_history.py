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
    if len(messages) < 3:
        return False
        
    total_length = sum(len(msg) for msg in messages)
    if total_length < 500:  # Skip very short conversations
        return False
        
    # Look for technical indicators
    technical_patterns = [
        r'```[a-z]*\n',  # Code blocks
        r'import\s+[a-zA-Z_]',  # Import statements
        r'def\s+[a-zA-Z_]',  # Function definitions
        r'class\s+[a-zA-Z_]',  # Class definitions
        r'git\s+[a-z]+',  # Git commands
        r'docker\s+[a-z]+',  # Docker commands
        r'npm\s+[a-z]+',  # NPM commands
        r'pip\s+[a-z]+',  # Pip commands
    ]
    
    content = '\n'.join(messages)
    for pattern in technical_patterns:
        if re.search(pattern, content):
            return True
            
    # Check title for technical terms
    technical_terms = ['code', 'programming', 'debug', 'error', 'function', 'api', 
                      'database', 'script', 'algorithm', 'docker', 'kubernetes']
    if any(term in title.lower() for term in technical_terms):
        return True
    
    return False

def extract_conversations(zip_path: Path) -> Dict:
    """
    Extract conversations from ChatGPT export zip file and convert to document format
    """
    documents = []
    tags = {
        "chatgpt": "Conversation exported from ChatGPT"
    }
    
    with zipfile.ZipFile(zip_path) as zf:
        # Find all conversation JSON files
        conv_files = [f for f in zf.namelist() if f.endswith('.json')]
        
        for conv_file in conv_files:
            with zf.open(conv_file) as f:
                conv_data = json.load(f)
                
                # Extract title and content
                title = conv_data.get('title', 'Untitled Conversation')
                
                # Combine messages into content
                messages = []
                for msg in conv_data.get('mapping', {}).values():
                    if 'message' in msg:
                        message = msg['message']
                        role = message.get('author', {}).get('role', '')
                        content = message.get('content', {}).get('parts', [''])[0]
                        messages.append(f"{role}: {content}")
                
                content = "\n\n".join(messages)
                
                # Only store interesting conversations
                if is_interesting_conversation(messages, title):
                    # Parse create time
                    create_time_str = conv_data.get('create_time', '')
                    try:
                        created_at = datetime.fromisoformat(create_time_str.replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        created_at = datetime.utcnow()
                    
                    # Create document directly in database
                    with Session(engine) as session:
                        document = Document(
                            title=title,
                            description="",  # Empty description as requested
                            content=content,
                            created_at=created_at,
                            updated_at=created_at
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
