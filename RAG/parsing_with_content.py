from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from .parsing_with_criteria import parse_with_criteria
from pathlib import Path
import numpy as np
import json
from dotenv import load_dotenv

load_dotenv()
embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")


def _concat_event_fields(event):
    """ Database에 있는 데이터 이벤트 중 title, description, location, member 필드를 조합하여 하나의 문자열로 만들기."""
    parts = []
    for key in ("title", "description", "location", "member"):
        if key not in event or event[key] is None:
            continue
        value = event[key]
        if isinstance(value, list):
            parts.append(" ".join(str(v) for v in value))
        else:
            parts.append(str(value))
    return " ".join(parts)


def embed_event(event: dict) -> dict:
    """단일 이벤트를 임베딩하여 embedding 필드에 저장"""
    text = _concat_event_fields(event)
    embedding = embedding_model.embed_query(text)
    event['embedding'] = embedding
    return event

def embed_events(events: list, vector_dir: str = "Database/[user]") -> str:
    """embedding 필드가 없는 이벤트들만 embed_event로 임베딩하고 원본 파일에 저장"""

    # Create directory if it doesn't exist
    vector_dir = Path(vector_dir)
    vector_dir.mkdir(parents=True, exist_ok=True)
    
    # Process only events without embedding
    events_to_embed = []
    for event in events:
        if 'embedding' not in event:
            events_to_embed.append(event)
    # Embed only events without embedding
    for event in events_to_embed:
        event = embed_event(event)
    
    # Load all JSON files, update events, and save back
    json_files = list(vector_dir.glob("*.json"))
    
    for json_file in json_files:
        try:
            # Load the file
            with open(json_file, 'r', encoding='utf-8') as f:
                file_events = json.load(f)
            
            # Update events with embeddings
            updated = False
            for file_event in file_events:
                # Find matching event in our events list
                for event in events_to_embed:
                    if event.get('id') == file_event.get('id'):
                        if 'embedding' in event and 'embedding' not in file_event:
                            file_event['embedding'] = event['embedding']
                            updated = True
                        break
            
            # Save back if updated
            if updated:
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(file_events, f, ensure_ascii=False, indent=2)
                print(f"Updated: {json_file.name}")
                
        except Exception as e:
            print(f"Error processing {json_file.name}: {e}")
    
    print(f"Embedded {len(events_to_embed)} events without embedding and updated original files")
    return str(vector_dir)


def parse_with_content(query: str, criteria=None, k: int = 10, vector_dir="Database/[user]") -> list:
    """Load matching events with pre-computed embeddings, create Chroma index, and search"""

    if not query:
        return []
    # Filter events by criteria (use parse_with_criteria which returns matching events)
    matched_events = parse_with_criteria(vector_dir, criteria=criteria or {})
    matched_ids = set(event['id'] for event in matched_events)
    # Filter events that match criteria
    matching_events = [event for event in matched_events if event['id'] in matched_ids]
    
    if not matching_events:
        return []
    
    # Create Chroma index using pre-computed embeddings
    texts = [_concat_event_fields(event) for event in matching_events]
    embeddings = [event["embedding"] for event in matching_events]
    metadatas = [{"event_json": json.dumps(event, ensure_ascii=False)} for event in matching_events]
    
    # Create Chroma index with pre-computed embeddings
    temp_index = Chroma(embedding_function=embedding_model)
    temp_index.add_texts(texts, metadatas=metadatas, embeddings=embeddings)
    
    # Search in the index
    docs = temp_index.similarity_search(query, k=k)
    
    # Extract results
    results = []
    for doc in docs:
        meta = getattr(doc, "metadata", {}) or {}
        ev_json = meta.get("event_json")
        if ev_json:
            try:
                results.append(json.loads(ev_json))
            except Exception:
                continue
    
    return results