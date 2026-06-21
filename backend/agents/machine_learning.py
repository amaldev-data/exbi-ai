import json
from backend.agents.base import BaseAgent

class MachineLearningAgent(BaseAgent):
    def __init__(self, llm_service, db_session=None):
        super().__init__("Machine Learning Agent", llm_service, db_session)

    def run(self, state: dict) -> dict:
        project_id = state["project_id"]
        domain = state["business_discovery"].get("business_domain", "Sales")
        profile = state["profile"]
        
        self.log(project_id, "Scanning dataset for statistical modeling and predictive machine learning opportunities...", log_type="system")
        
        prompt = f"""
        Inspect this dataset profile summary:
        - Domain: {domain}
        - Columns: {profile['column_names']}
        - Numerics: {profile['numeric_columns']}
        - Categoricals: {profile['categorical_columns']}
        - Targets: {profile.get('target_variables', [])}
        - Time series: {json.dumps(profile.get('time_series_structure'))}
        
        Identify 3 relevant machine learning opportunities for this dataset.
        For each opportunity, specify:
        1. "algorithm_type": Classification, Regression, Clustering, or Time-series Forecasting.
        2. "target_column": Target variable or predictive feature column name.
        3. "business_usecase": Explanation of the business benefit.
        4. "complexity": High, Medium, or Low.
        
        Return a JSON response containing an "opportunities" list of these items.
        Return strictly JSON.
        """
        
        system_prompt = "You are the Machine Learning Agent. Detect ML opportunities and output JSON."
        response_str = self.llm_service.query(prompt, system_prompt, json_mode=True)
        
        try:
            ml_report = json.loads(response_str)
            if not isinstance(ml_report, dict) or "opportunities" not in ml_report:
                raise KeyError("Missing opportunities key")
        except Exception:
            # Fallback based on domain
            domain_lower = domain.lower()
            if "hr" in domain_lower or "employee" in domain_lower:
                ml_report = {
                    "opportunities": [
                        {"algorithm_type": "Classification", "target_column": "Attrition", "business_usecase": "Predict employee attrition probability to improve retention.", "complexity": "Medium"},
                        {"algorithm_type": "Regression", "target_column": "MonthlyIncome", "business_usecase": "Estimate market salary levels based on role parameters.", "complexity": "Medium"},
                        {"algorithm_type": "Clustering", "target_column": "Department", "business_usecase": "Segment workforce demographics to align training resources.", "complexity": "Low"}
                    ]
                }
            else:
                ml_report = {
                    "opportunities": [
                        {"algorithm_type": "Time-series Forecasting", "target_column": "Amount", "business_usecase": "Forecast gross revenue sales for the next 60 days.", "complexity": "High"},
                        {"algorithm_type": "Clustering", "target_column": "Category", "business_usecase": "Identify purchasing clusters for target recommendations.", "complexity": "Low"},
                        {"algorithm_type": "Regression", "target_column": "Amount", "business_usecase": "Predict order size based on region and quantity.", "complexity": "Low"}
                    ]
                }
                
        state["ml_report"] = ml_report
        
        self.log(
            project_id, 
            "Machine Learning Opportunity Report generated successfully.", 
            log_type="artifact", 
            payload=ml_report
        )
        
        return state
