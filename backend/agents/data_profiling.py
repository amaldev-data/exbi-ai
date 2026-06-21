import json
from backend.agents.base import BaseAgent
from backend.services.data_engine import DataEngine

class DataProfilingAgent(BaseAgent):
    def __init__(self, llm_service, db_session=None):
        super().__init__("Data Profiling Agent", llm_service, db_session)
        self.data_engine = DataEngine()

    def run(self, state: dict) -> dict:
        project_id = state["project_id"]
        file_path = state["file_path"]
        
        self.log(project_id, "Inspecting raw dataset column distributions and data shapes...", log_type="system")
        
        try:
            df = self.data_engine.load_dataset(file_path)
            profile = self.data_engine.profile_dataset(df)
            state["profile"] = profile
            
            self.log(
                project_id, 
                f"Statistical profiling complete. Found {profile['total_missing']} missing cells and {profile['duplicate_count']} duplicate records.", 
                log_type="artifact", 
                payload=profile
            )
        except Exception as e:
            self.log(project_id, f"Profiling failed: {str(e)}", log_type="error")
            raise e
            
        return state
