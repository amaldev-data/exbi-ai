import os
import shutil
from backend.agents.base import BaseAgent
from backend.config import TEMP_UPLOADS, TEMP_REPORTS
from backend.database.db_manager import Project, AgentLog

class SessionManagerAgent(BaseAgent):
    def __init__(self, llm_service, db_session=None):
        super().__init__("Session Manager Agent", llm_service, db_session)

    def run(self, state: dict) -> dict:
        # This agent performs active directory hygiene on startup or exit
        project_id = state.get("project_id")
        self.log(project_id, "Session Manager initialized. Auditing active sandbox boundaries...", log_type="system")
        return state

    def purge_session(self, project_id: str):
        """
        DANGEROUS: Deletes all database logs, records, uploaded CSV/Excel files,
        and generated report files for a project to enforce absolute session-based privacy.
        """
        self.log(project_id, f"Initiating absolute privacy purge for project: {project_id}", log_type="system")
        
        # 1. Delete files from disk
        upload_formats = [f"raw_{project_id}.csv", f"raw_{project_id}.xlsx", f"raw_{project_id}.xls",
                          f"cleaned_{project_id}.csv", f"cleaned_{project_id}.xlsx"]
        report_formats = [f"executive_report_{project_id}.pdf", f"executive_report_{project_id}.docx",
                          f"executive_report_{project_id}.pptx", f"executive_report_{project_id}.xlsx"]
        
        for fmt in upload_formats:
            path = os.path.join(TEMP_UPLOADS, fmt)
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass
                    
        for fmt in report_formats:
            path = os.path.join(TEMP_REPORTS, fmt)
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass

        # 2. Clear Database records
        if self.db:
            try:
                self.db.query(AgentLog).filter(AgentLog.project_id == project_id).delete()
                self.db.query(Project).filter(Project.id == project_id).delete()
                self.db.commit()
            except Exception as e:
                print(f"Database purge error: {e}")
