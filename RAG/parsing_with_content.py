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


def embed_events(events, vector_dir="RAG/VectorDB/user"):
    """이벤트 별로 문자열을 조합하여 임베딩하고 JSON 파일로 저장하기
    이렇게 하면 하나의 이벤트를 하나의 context로 처리할 수 있음"""

    # Create directory if it doesn't exist
    vector_dir = Path(vector_dir)
    vector_dir.mkdir(parents=True, exist_ok=True)
    
    # Clear existing files
    for file in vector_dir.glob("*.json"):
        file.unlink()
    
    # Process each event
    for event in enumerate(events):
        text = _concat_event_fields(event)
        # Generate embedding for this text
        embedding = embedding_model.embed_query(text)
        # Save event with embedding
        event_data = {
            "event": event,
            "text": text,
            "embedding": embedding
        }
        
        event_file = vector_dir / f"event_id:{event['id']}.json"
        with open(event_file, 'w', encoding='utf-8') as f:
            json.dump(event_data, f, ensure_ascii=False, indent=2)
    
    print(f"Embedded and saved {len(events)} events to {vector_dir}")
    return vector_dir


def parse_with_content(query: str, criteria=None, k: int = 10, vector_dir="RAG/VectorDB/user"):
    """Load matching events with pre-computed embeddings, create Chroma index, and search"""

    if not query:
        return []
    
    vector_dir = Path(vector_dir)
    if not vector_dir.exists():
        return []
    
    # Find all JSON files
    json_files = list(vector_dir.glob("event_*.json"))
    if not json_files:
        return []
    
    # Load all event data from JSON files
    all_event_data = []
    for json_file in sorted(json_files):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                event_data = json.load(f)
                all_event_data.append(event_data)
        except Exception as e:
            print(f"Failed to load {json_file}: {e}")
            continue
    
    if not all_event_data:
        return []
    
    # Filter events by criteria (use parse_with_criteria which returns matching events)
    all_events = [data["event"] for data in all_event_data]
    matched_events = parse_with_criteria(all_events, criteria or {})
    matched_ids = set(map(id, matched_events))
    matching_event_data = [data for i, data in enumerate(all_event_data) if id(all_events[i]) in matched_ids]

    
    if not matching_event_data:
        return []
    
    # Create Chroma index using pre-computed embeddings
    texts = [data["text"] for data in matching_event_data]
    embeddings = [data["embedding"] for data in matching_event_data]
    metadatas = [{"event_json": json.dumps(data["event"], ensure_ascii=False)} for data in matching_event_data]
    
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