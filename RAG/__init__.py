from .parsing_with_criteria import parse_with_criteria
from .parsing_with_content import embed_events, parse_with_content, embed_event


class RAG:
    def __init__(self, events):
        self.events = events
        self.embeddings = embed_events(events)

    def _embed_events(self, events):
        return embed_events(events, vector_dir="Database/[user]")
    def embed_event(self, event: dict) -> dict:
        return embed_event(event, vector_dir="Database/[user]")
    def parse_with_criteria(self, events=None, criteria=None):
        if events is None:
            events = self.events
        return parse_with_criteria(events, criteria)
    def parse_with_content(self, query=None, criteria=None, k=10, vector_dir="Database/[user]"):
        return parse_with_content(query, criteria, k, vector_dir="Database/[user]")
