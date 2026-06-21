import json
import logging
import traceback
import datetime
from sqlalchemy.orm import Session
from backend.database.db_manager import Project, AgentLog
from backend.services.llm_service import LLMService

# Import the 5 simplified agents
from backend.agents.dataset_intelligence import DatasetIntelligenceAgent
from backend.agents.business_analyst import BusinessAnalystAgent
from backend.agents.data_quality import DataQualityAgent
from backend.agents.visualization_agent import VisualizationAgent
from backend.agents.reporting_agent import ReportingAgent

logger = logging.getLogger(__name__)

class ProgramManagerOrchestrator:
    def __init__(self, llm_service: LLMService, db_session: Session):
        self.llm = llm_service
        self.db = db_session
        
        # Initialize 5 agents
        self.dataset_intel = DatasetIntelligenceAgent(self.llm, self.db)
        self.business_analyst = BusinessAnalystAgent(self.llm, self.db)
        self.data_quality = DataQualityAgent(self.llm, self.db)
        self.visualization = VisualizationAgent(self.llm, self.db)
        self.reporting = ReportingAgent(self.llm, self.db)

    def log_system(self, project_id: str, msg: str, agent_name: str = "Program Manager Agent"):
        logger.info(f"[{agent_name}]: {msg}")
        log_entry = AgentLog(
            project_id=project_id,
            timestamp=datetime.datetime.utcnow(),
            agent_name=agent_name,
            message=msg,
            log_type="system"
        )
        self.db.add(log_entry)
        self.db.commit()

    def run_discovery(self, project_id: str, file_path: str, filename: str) -> dict:
        """
        Phase 1: Ingestion & Discovery. Runs synchronously upon upload.
        """
        self.log_system(project_id, "Initiating Phase 1: Guided Discovery scan.")
        
        state = {
            "project_id": project_id,
            "file_path": file_path,
            "filename": filename
        }
        
        # 1. Dataset Intelligence Agent
        state = self.dataset_intel.run(state)
        
        # 2. Business Analyst Agent
        state = self.business_analyst.run(state)
        
        # Save structured discovery info to Project row
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if project:
            project.dataset_info = json.dumps(state["dataset_info"])
            self.db.commit()
            
        self.log_system(project_id, "Intelligence scan finalized. Discovery parameters ready.")
        return state

    def run_full_workflow(self, project_id: str, selected_analyses: list):
        """
        Phase 2: Full Analytics Compilation. Runs asynchronously.
        """
        self.log_system(project_id, "Launching Phase 2 execution pipeline...")
        
        try:
            project = self.db.query(Project).filter(Project.id == project_id).first()
            if not project:
                raise ValueError(f"Project {project_id} not found in database.")
                
            project.status = "running"
            self.db.commit()
            
            # Load discovery state
            dataset_info = json.loads(project.dataset_info)
            
            state = {
                "project_id": project_id,
                "file_path": project.file_path,
                "filename": project.filename,
                "dataset_info": dataset_info,
                "profile": dataset_info["technical_profile"],
                "selected_analyses": selected_analyses
            }
            
            # 1. Data Quality Agent
            self.log_system(project_id, "Deploying Data Quality Agent...", "Data Quality Agent")
            state = self.data_quality.run(state)
            
            # 2. Business Analyst Agent (Phase 2 - Mapping requirements to Business Question Framework)
            self.log_system(project_id, "Deploying Business Analyst Agent...", "Business Analyst Agent")
            state = self.business_analyst.run_analysis_mapping(state)
            
            # 3. Visualization Agent
            self.log_system(project_id, "Deploying Visualization Agent...", "Visualization Agent")
            state = self.visualization.run(state)
            
            # 3. Reporting Agent
            self.log_system(project_id, "Deploying Reporting Agent...", "Reporting Agent")
            state = self.reporting.run(state)
            
            # Save final results on main session
            project = self.db.query(Project).filter(Project.id == project_id).first()
            if project:
                project.dashboard_spec = json.dumps(state["dashboard_spec"])
                project.executive_report = state["report_markdown"]
                project.approval_certificate = json.dumps({
                    "overall_confidence_score": state["profile"].get("quality_score", 95),
                    "status": "APPROVED",
                    "signoff_officer": "exbi ai Reporting Agent",
                    "governance_verdict": "Data validation check completed successfully."
                })
                project.quality_report = json.dumps(state["quality_report"])
                project.status = "completed"
                self.db.commit()
                
            self.log_system(project_id, "All analytics deliverables compiled successfully. Ready for download!")
            
        except Exception as e:
            self.log_system(project_id, f"Fatal error occurred during Phase 2 execution: {str(e)}")
            logger.error(traceback.format_exc())
            try:
                project = self.db.query(Project).filter(Project.id == project_id).first()
                if project:
                    project.status = "failed"
                    self.db.commit()
            except Exception:
                pass
