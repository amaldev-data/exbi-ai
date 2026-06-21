import json
from backend.agents.base import BaseAgent

class SemanticMappingAgent(BaseAgent):
    def __init__(self, llm_service, db_session=None):
        super().__init__("Semantic Mapping Agent", llm_service, db_session)

    def run(self, state: dict) -> dict:
        project_id = state["project_id"]
        profile = state["profile"]
        
        self.log(project_id, "Analyzing dataset semantics to map variables to analytical dimensions...", log_type="system")
        
        prompt = f"""
        Analyze these column names and their sample summaries:
        - Columns: {profile['column_names']}
        - Datatypes: {json.dumps(profile['data_types'])}
        - Detected numeric lists: {profile['numeric_columns']}
        - Detected categorical lists: {profile['categorical_columns']}
        
        Perform a semantic mapping of these columns. Map them into standard BI concepts:
        1. "metrics": List of numerical columns tracking performance (e.g., Revenue, Profit, Salary, MonthlyCharges).
        2. "dimensions": Categorical variables to group by (e.g., Category, Department, Country).
        3. "date_columns": Date/Time/Year/Month columns.
        4. "geographic_columns": Columns representing geography (e.g., Region, Country, City, ZIP).
        5. "financial_columns": Columns tracking financial amounts (e.g., revenue, salary, cost, price).
        6. "customer_columns": Customer-related identifiers or demographics (e.g., CustomerID, Age, Tenure).
        
        Return a JSON containing these 6 mapped array structures. Ensure all columns in the dataset are categorized correctly.
        Return strictly JSON.
        """
        
        system_prompt = "You are the Semantic Mapping Agent. Output semantic groupings in JSON format."
        response_str = self.llm_service.query(prompt, system_prompt, json_mode=True)
        
        try:
            mappings = json.loads(response_str)
            if not isinstance(mappings, dict) or "metrics" not in mappings:
                raise KeyError("Missing metrics key")
        except Exception:
            # Fallback using technical profile lists
            mappings = {
                "metrics": profile.get("currency_fields", []) + profile.get("percentage_fields", []) + [c for c in profile.get("numeric_columns", []) if c not in profile.get("primary_keys", [])],
                "dimensions": [c for c in profile.get("categorical_columns", []) if c not in profile.get("geographical_fields", []) and c not in profile.get("target_variables", [])],
                "date_columns": profile.get("date_columns", []),
                "geographic_columns": profile.get("geographical_fields", []),
                "financial_columns": profile.get("currency_fields", []),
                "customer_columns": profile.get("target_variables", []) + [c for c in profile.get("column_names", []) if "cust" in c.lower() or "client" in c.lower() or "emp" in c.lower()]
            }
            
        state["semantic_mappings"] = mappings
        
        self.log(
            project_id, 
            "Semantic column mapping complete. Metrics, dimensions, and entities defined.", 
            log_type="artifact", 
            payload=mappings
        )
        
        return state
