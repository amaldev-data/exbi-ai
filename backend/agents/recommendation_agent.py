import json
from backend.agents.base import BaseAgent
from backend.database.db_manager import Project

class RequirementRecommendationAgent(BaseAgent):
    def __init__(self, llm_service, db_session=None):
        super().__init__("Requirement Recommendation Agent", llm_service, db_session)

    def run(self, state: dict) -> dict:
        project_id = state["project_id"]
        dataset_info = state["dataset_info"]
        
        self.log(project_id, "Formulating custom analytical recommendations based on data profile...", log_type="system")
        
        business_domain = dataset_info["business_discovery"].get("business_domain", "")
        cols = dataset_info["technical_profile"].get("column_names", [])
        
        prompt = f"""
        Based on the following dataset profile:
        - Domain: {business_domain}
        - Columns: {cols}
        
        Generate a list of 6 analytical dashboard pages/reports that would be highly useful.
        For each, provide:
        1. "id": A unique string key (e.g., "sales_trends")
        2. "title": A professional label (e.g., "Sales & Revenue Trend Analysis")
        3. "description": A short explanation of the value this analysis brings.
        4. "recommended": Boolean, set to true if the columns indicate it is highly relevant.
        5. "reason": A short explanation of why this was recommended based on domain and columns.
        
        Return the result as a JSON array of objects.
        """
        
        system_prompt = "You are the Requirement Recommendation Agent. Suggest relevant analyses in JSON array format."
        
        response_str = self.llm_service.query(prompt, system_prompt, json_mode=True)
        
        try:
            recommendations = json.loads(response_str)
        except Exception:
            # Fallback recommendations if JSON load fails
            domain_lower = business_domain.lower()
            if "sales" in domain_lower or "revenue" in domain_lower:
                domain_type = "sales"
            elif "hr" in domain_lower or "employee" in domain_lower:
                domain_type = "hr"
            elif "churn" in domain_lower or "customer" in domain_lower:
                domain_type = "churn"
            else:
                domain_type = "general"

            recommendations = [
                {
                    "id": "sales_analysis", 
                    "title": "Sales & Revenue Trend Analysis", 
                    "description": "Inspect sales performance over time, identify peak sales, and model seasonality.", 
                    "recommended": domain_type == "sales",
                    "reason": "Recommended because your dataset contains currency values and timestamp metrics to analyze performance over time."
                },
                {
                    "id": "profit_analysis", 
                    "title": "Profitability & Margin Breakdown", 
                    "description": "Segment products or departments to identify highest margins.", 
                    "recommended": domain_type == "sales",
                    "reason": "Recommended because your dataset has financial categories and profit indicators to isolate cost and profit drivers."
                },
                {
                    "id": "customer_seg", 
                    "title": "Customer Demographic Segmentation", 
                    "description": "Cluster users based on purchasing behavior.", 
                    "recommended": domain_type == "churn" or domain_type == "sales",
                    "reason": "Recommended because your dataset has categorical groupings and segments to separate customer profiles."
                },
                {
                    "id": "churn_analysis", 
                    "title": "Churn Risk & Retention Modeling", 
                    "description": "Identify main churn drivers and flag high-risk customers.", 
                    "recommended": domain_type == "churn",
                    "reason": "Recommended because your dataset tracks customer status and churn indicators to model retention rates."
                },
                {
                    "id": "hr_attrition", 
                    "title": "Employee Attrition Analysis", 
                    "description": "Pinpoint demographic and financial indicators linked to employee turnover.", 
                    "recommended": domain_type == "hr",
                    "reason": "Recommended because your dataset contains employee attrition markers, age groups, and tenure metrics."
                },
                {
                    "id": "forecasting", 
                    "title": "Time Series Forecasting (Next 60 Days)", 
                    "description": "Forecast key metric performance using automated estimations.", 
                    "recommended": True,
                    "reason": "Recommended because forecasting trends is critical for anticipating resource allocation and demand changes."
                }
            ]

        state["recommendations"] = recommendations
        
        # Save to database
        if self.db:
            project = self.db.query(Project).filter(Project.id == project_id).first()
            if project:
                # We can store recommendations temporarily in selected_analyses or handle it via a separate endpoint.
                # Let's save the suggestions as selected_analyses by default, and update when the user posts their choice.
                project.selected_analyses = json.dumps(recommendations)
                self.db.commit()
                
        self.log(
            project_id, 
            f"Generated {len(recommendations)} analytical suggestions for selection.", 
            log_type="artifact", 
            payload=recommendations
        )
        
        return state
