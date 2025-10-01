import os
import json
from typing import Dict, List, Any

def delete_event(event_id: int, file_path: str) -> bool:
    """
    Delete an event by ID from the specified JSON file.
    
    Args:
        event_id (int): The ID of the event to delete
        file_path (str): The path to the JSON file
        
    Returns:
        bool: True if event was found and deleted, False otherwise
    """
    if not os.path.exists(file_path):
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        events = json.load(f)
    
    # Find and remove the event with the specified ID
    original_count = len(events)
    events = [event for event in events if event.get('id') != event_id]
    
    if len(events) < original_count:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(events, f, ensure_ascii=False, indent=2)
        return True
    return False

def add_event(event_data: Dict[str, Any], file_path: str) -> int:
    """
    Add a new event to the specified JSON file.
    
    Args:
        event_data (Dict[str, Any]): The event data to add
        file_path (str): The path to the JSON file
        
    Returns:
        int: The ID of the newly created event
    """
    # Load existing events or create empty list
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            events = json.load(f)
    else:
        events = []
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Generate new ID
    if not events:
        new_id = 1
    else:
        new_id = max(event.get('id', 0) for event in events) + 1
    
    # Create new event with the generated ID
    new_event = event_data.copy()
    new_event['id'] = new_id
    
    # Add the new event to the list
    events.append(new_event)
    
    # Save the updated events
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    
    return new_id
