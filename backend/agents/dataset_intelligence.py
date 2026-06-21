import json
import pandas as pd
import numpy as np
from backend.agents.base import BaseAgent
from backend.database.db_manager import Project
from backend.services.data_engine import DataEngine

class DatasetIntelligenceAgent(BaseAgent):
    def __init__(self, llm_service, db_session=None):
        super().__init__("Dataset Intelligence Agent", llm_service, db_session)
        self.data_engine = DataEngine()

    def run(self, state: dict) -> dict:
        project_id = state["project_id"]
        file_path = state["file_path"]
        filename = state["filename"]
        
        self.log(project_id, "Analyzing dataset structure, classifications, and domain context...", log_type="system")
        
        # Load and profile dataset
        df = self.data_engine.load_dataset(file_path)
        profile = self.data_engine.profile_dataset(df)
        
        # Detect domain using LLM
        prompt = f"""
        Analyze the columns and statistical profile of this dataset:
        - Filename: {filename}
        - Total Rows: {profile['rows']}
        - Total Columns: {profile['columns']}
        - Column Names: {profile['column_names']}
        - Data Types: {profile['data_types']}
        
        Determine the primary business domain and summarize the business context in 1-2 sentences.
        Available domains: "Sales & Revenue", "Human Resources", "Customer Churn", "Operations Performance".
        
        Return a JSON response with exactly two keys:
        - "business_domain": one of the four domains listed above
        - "business_context": a 1-2 sentence description of the dataset context
        
        Return strictly JSON.
        """
        
        system_prompt = "You are the Dataset Intelligence Agent. Classify dataset domains and context."
        response_str = self.llm_service.query(prompt, system_prompt, json_mode=True)
        
        try:
            domain_info = json.loads(response_str)
            if not isinstance(domain_info, dict) or "business_domain" not in domain_info:
                raise KeyError()
        except Exception:
            # Fallback based on name/columns
            col_str = " ".join(profile['column_names']).lower()
            if any(k in col_str for k in ["sales", "revenue", "amount", "price"]):
                domain = "Sales & Revenue"
            elif any(k in col_str for k in ["employee", "salary", "attrition"]):
                domain = "Human Resources"
            elif any(k in col_str for k in ["churn", "customer", "charges"]):
                domain = "Customer Churn"
            else:
                domain = "Operations Performance"
                
            domain_info = {
                "business_domain": domain,
                "business_context": f"Analytical profile for dataset {filename} in the {domain} domain."
            }
            
        profile["business_discovery"] = domain_info
        
        # Save to state
        state["profile"] = profile
        state["dataset_info"] = {
            "technical_profile": profile,
            "business_discovery": domain_info,
            "semantic_mappings": profile.get("column_classifications", {}),
            "relationships": profile.get("relationships", [])
        }
        
        self.log(project_id, f"Dataset Intelligence scan complete. Detected domain: {domain_info['business_domain']}", log_type="system")
        return state
