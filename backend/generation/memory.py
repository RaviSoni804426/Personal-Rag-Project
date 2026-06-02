import json
from typing import List, Dict, Any
from backend.database.connection import SessionLocal
from backend.database.models import QueryLog

class ConversationalMemory:
    def __init__(self, max_history_turns: int = 6):
        self.max_history_turns = max_history_turns

    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        """Retrieves history for a given session, formatted for LLM ingestion."""
        if not session_id or session_id == "default":
            return []

        db = SessionLocal()
        messages = []
        try:
            # Query recent logs in chronological order
            logs = db.query(QueryLog)\
                     .filter(QueryLog.session_id == session_id)\
                     .order_by(QueryLog.created_at.asc())\
                     .all()
            
            # Keep only the last N turns to avoid buffer bloat
            recent_logs = logs[-self.max_history_turns:]
            
            for log in recent_logs:
                messages.append({"role": "user", "content": log.query})
                messages.append({"role": "assistant", "content": log.response})
        except Exception as e:
            print(f"Memory read error: {e}")
        finally:
            db.close()
            
        return messages

    def get_history_summary_context(self, session_id: str) -> str:
        """Helper to serialize recent messages as a clean text block."""
        history = self.get_history(session_id)
        if not history:
            return ""
        
        summary = "\n--- Conversation History ---\n"
        for msg in history:
            role = "User" if msg["role"] == "user" else "Assistant"
            summary += f"{role}: {msg['content']}\n"
        summary += "-----------------------------\n"
        return summary
