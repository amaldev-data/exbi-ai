import json
from backend.agents.base import BaseAgent
from backend.database.db_manager import Project

class AnalyticsStrategyAgent(BaseAgent):
    def __init__(self, llm_service, db_session=None):
        super().__init__("Analytics Strategy Agent", llm_service, db_session)

    def run(self, state: dict) -> dict:
        project_id = state["project_id"]
        brd = state["business_requirements"]
        dataset_info = state["dataset_info"]
        user_inputs = state.get("user_inputs", {})
        level = user_inputs.get("level", "Executive summary analysis")
        
        self.log(project_id, "Formulating custom Technical Execution Roadmap...", log_type="system")
        
        prompt = f"""
        Formulate a structured Analytics Strategy JSON for:
        - Business Requirements: {json.dumps(brd)}
        - Analysis Scope: {level}
        - Domain: {dataset_info.get('business_discovery', {}).get('business_domain', 'General')}
        - Technical Profile: {json.dumps(dataset_info['technical_profile'])}
        
        Provide JSON containing:
        1. "objectives": 1-sentence analytical strategy objective.
        2. "roadmap": A list of 4 roadmap phases.
        3. "department_responsibilities": Key instructions for: Data Quality, Visualization, Reporting, and Executive Review.
        4. "validation_rules": Rules to govern calculations.
        
        Return strictly JSON.
        """
        
        system_prompt = "You are the Analytics Strategy Agent. Create structured Technical Strategy JSON."
        response_str = self.llm_service.query(prompt, system_prompt, json_mode=True)
        
        try:
            strategy = json.loads(response_str)
            if not isinstance(strategy, dict) or "objectives" not in strategy:
                raise KeyError("Missing objectives key")
        except Exception:
            strategy = {
                "objectives": f"Deliver structured {level} insights for {dataset_info.get('business_discovery', {}).get('business_domain')} operations.",
                "roadmap": [
                    "Phase 1: Automated cleansing & outliers trimming.",
                    "Phase 2: Semantic mapping and KPI formulation.",
                    "Phase 3: Grid visualization and Chart.js code generation.",
                    "Phase 4: Consulting report compilation and compliance validation."
                ],
                "department_responsibilities": {
                    "Data Quality": "Standardize columns, clean outliers, impute missing cells.",
                    "Visualization": "Render trend lines, category bars, and donut splits in Chart.js.",
                    "Reporting": "Synthesize data segments into markdown findings and actions.",
                    "Governance": "Validate formulas, verify data bounds, check compliance."
                },
                "validation_rules": [
                    "Numerical fields must match range profiles.",
                    "Chart totals must equal base column aggregations."
                ]
            }

        state["analytics_strategy"] = strategy
        
        # Save to database
        if self.db:
            project = self.db.query(Project).filter(Project.id == project_id).first()
            if project:
                project.analytics_strategy = json.dumps(strategy)
                self.db.commit()
                
        self.log(
            project_id, 
            "Technical Execution Plan completed. Core analytical strategy formulated.", 
            log_type="artifact", 
            payload=strategy
        )
        
        return state
