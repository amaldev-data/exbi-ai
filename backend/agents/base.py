import datetime
import json
from backend.database.db_manager import AgentLog, Project
from backend.services.llm_service import LLMService

class BaseAgent:
    def __init__(self, name: str, llm_service: LLMService, db_session=None):
        self.name = name
        self.llm_service = llm_service
        self.db = db_session

    def set_session(self, db_session):
        self.db = db_session

    def log(self, project_id: str, message: str, log_type: str = 'system', target_agent: str = None, payload: dict = None):
        """
        Record a log entry or message inside the SQLite database for real-time frontend monitoring.
        """
        payload_str = json.dumps(payload) if payload else None
        log_entry = AgentLog(
            project_id=project_id,
            timestamp=datetime.datetime.utcnow(),
            agent_name=self.name,
            target_agent=target_agent,
            message=message,
            log_type=log_type,
            payload=payload_str
        )
        if self.db:
            self.db.add(log_entry)
            self.db.commit()
        else:
            print(f"[{self.name} -> {target_agent or 'System'} ({log_type})]: {message}")

    def update_project_status(self, project_id: str, status: str):
        if self.db:
            project = self.db.query(Project).filter(Project.id == project_id).first()
            if project:
                project.status = status
                self.db.commit()

    def run(self, state: dict) -> dict:
        """
        Execute agent logic. Override in subclasses.
        """
        raise NotImplementedError("Each agent subclass must implement its own run method.")
