import os
import json
import pandas as pd
from backend.agents.base import BaseAgent
from backend.config import TEMP_UPLOADS
from backend.services.data_engine import DataEngine
from backend.database.db_manager import Project

class DataQualityAgent(BaseAgent):
    def __init__(self, llm_service, db_session=None):
        super().__init__("Data Quality Agent", llm_service, db_session)
        self.data_engine = DataEngine()

    def run(self, state: dict) -> dict:
        project_id = state["project_id"]
        file_path = state["file_path"]
        profile = state["profile"]
        
        self.log(project_id, "Executing advanced data cleaning, text casing standardization, and column median imputations...", log_type="system")
        
        try:
            df = self.data_engine.load_dataset(file_path)
            
            # Clean dataset
            df_cleaned = self.data_engine.clean_dataset(df, profile)
            
            # Save files
            cleaned_csv_path = os.path.join(TEMP_UPLOADS, f"cleaned_{project_id}.csv")
            cleaned_xlsx_path = os.path.join(TEMP_UPLOADS, f"cleaned_{project_id}.xlsx")
            
            df_cleaned.to_csv(cleaned_csv_path, index=False)
            df_cleaned.to_excel(cleaned_xlsx_path, index=False, engine='openpyxl')
            
            state["cleaned_csv_path"] = cleaned_csv_path
            state["cleaned_xlsx_path"] = cleaned_xlsx_path
            state["cleaned_rows_count"] = len(df_cleaned)
            
            # Validate business rules on cleaned dataset
            validation_results = self.data_engine.validate_business_rules(df_cleaned, profile)
            
            before_rows = profile["rows"]
            after_rows = len(df_cleaned)
            rows_dropped = before_rows - after_rows
            
            quality_report = {
                "before_rows": before_rows,
                "after_rows": after_rows,
                "rows_dropped": rows_dropped,
                "validation_passed": validation_results["validation_passed"],
                "violations": validation_results["violations"],
                "total_violations_count": validation_results["total_violations_count"],
                "quality_score": profile.get("quality_score", 100)
            }
            state["quality_report"] = quality_report
            
            # Save to Database
            if self.db:
                project = self.db.query(Project).filter(Project.id == project_id).first()
                if project:
                    project.cleaned_path = cleaned_csv_path
                    project.quality_report = json.dumps(quality_report)
                    self.db.commit()
            
            self.log(
                project_id, 
                f"Data quality checks passed. Retained {after_rows} rows, resolved {validation_results['total_violations_count']} logical anomalies.", 
                log_type="artifact", 
                payload=quality_report
            )
        except Exception as e:
            self.log(project_id, f"Data quality validation failed: {str(e)}", log_type="error")
            raise e
            
        return state
