import sys
import json
import zipfile
from pathlib import Path
from typing import Dict, List
from datetime import datetime
from app.models import Document, Tag
from utils.load_data import load_data

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
                
                # Create document entry
                doc = {
                    "title": title,
                    "description": f"ChatGPT conversation from {conv_data.get('create_time', '')}",
                    "content": content,
                    "tags": ["chatgpt"]
                }
                documents.append(doc)
    
    return {
        "tags": tags,
        "documents": documents
    }

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
    
    # Extract conversations and convert to document format
    data = extract_conversations(zip_path)
    
    # Create temporary JSON file
    with Path('temp_conversations.json').open('w') as f:
        json.dump(data, f)
    
    # Load data into database
    load_data(Path('temp_conversations.json'))
    
    # Clean up temp file
    Path('temp_conversations.json').unlink()
    print("ChatGPT conversations loaded successfully!")

if __name__ == "__main__":
    main()
