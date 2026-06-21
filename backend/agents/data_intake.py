import os
from backend.agents.base import BaseAgent
from backend.services.data_engine import DataEngine

class DataIntakeAgent(BaseAgent):
    def __init__(self, llm_service, db_session=None):
        super().__init__("Data Intake Agent", llm_service, db_session)
        self.data_engine = DataEngine()

    def run(self, state: dict) -> dict:
        project_id = state["project_id"]
        file_path = state["file_path"]
        
        self.log(project_id, f"Intaking dataset: {os.path.basename(file_path)}", log_type="system")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Dataset path {file_path} not found.")
            
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in ['.csv', '.xlsx', '.xls']:
            raise ValueError(f"Intake rejected: unsupported format '{ext}'. Only CSV, XLSX, XLS allowed.")
            
        try:
            df = self.data_engine.load_dataset(file_path)
            state["raw_shape"] = df.shape
            self.log(project_id, f"File successfully loaded. Rows: {df.shape[0]}, Columns: {df.shape[1]}.", log_type="system")
        except Exception as e:
            self.log(project_id, f"Failed to ingest dataset: {str(e)}", log_type="error")
            raise e
            
        return state
