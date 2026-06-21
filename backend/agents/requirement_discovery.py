import json
from backend.agents.base import BaseAgent
from backend.database.db_manager import Project

class RequirementDiscoveryAgent(BaseAgent):
    def __init__(self, llm_service, db_session=None):
        super().__init__("Requirement Discovery Agent", llm_service, db_session)

    def run(self, state: dict) -> dict:
        project_id = state["project_id"]
        selected = state.get("selected_analyses", [])
        dataset_info = state.get("dataset_info", {})
        
        user_inputs = state.get("user_inputs", {})
        problem = user_inputs.get("problem", "General operational reporting")
        decision = user_inputs.get("decision", "Monitor operational thresholds")
        audience = user_inputs.get("audience", "Department Managers")
        objective = user_inputs.get("objective", "KPI Monitoring")
        level = user_inputs.get("level", "Executive summary analysis")

        self.log(project_id, "Synthesizing stakeholder objectives and expected outcomes...", log_type="system")
        
        prompt = f"""
        Define a structured Business Requirement Document (BRD) JSON for:
        - Business Problem: {problem}
        - Core Decision: {decision}
        - Stakeholder Audience: {audience}
        - Core Objective: {objective}
        - Analysis Scope: {level}
        - Chosen Analyses: {selected}
        - Dataset Domain: {dataset_info.get('business_discovery', {}).get('business_domain', 'General')}
        
        Provide JSON containing:
        1. "business_goals": 3 core business goals.
        2. "success_metrics": 3 success indicators.
        3. "deliverables": List of analytical deliverables.
        4. "risks": 2 project risks.
        5. "constraints": 2 constraints.
        
        Return strictly JSON.
        """
        
        system_prompt = "You are the Requirement Discovery Agent. Create structured requirements JSON."
        response_str = self.llm_service.query(prompt, system_prompt, json_mode=True)
        
        try:
            brd = json.loads(response_str)
            if not isinstance(brd, dict) or "business_goals" not in brd:
                raise KeyError("Missing business_goals key")
        except Exception:
            brd = {
                "business_goals": [
                    f"Address core business challenge: {problem}.",
                    f"Deliver description metrics to support: {decision}.",
                    f"Tailor dashboard views for {audience}."
                ],
                "success_metrics": [
                    f"Deliver analytical panels formatted for {audience}.",
                    "Ensure statistical integrity on numerical columns.",
                    f"Achieve objective: {objective}."
                ],
                "deliverables": [
                    "Cleaned and imputed CSV/Excel dataset.",
                    "Dynamic dashboard layout specifications.",
                    "Strategic executive report summary."
                ],
                "risks": [
                    "Potential bias if categoricals are highly skewed.",
                    "Data completeness limitations if source files have missing values."
                ],
                "constraints": [
                    "Analysis must run within browser session parameters.",
                    "Compliance validation checks required prior to export."
                ]
            }

        state["business_requirements"] = brd
        
        # Save to database
        if self.db:
            project = self.db.query(Project).filter(Project.id == project_id).first()
            if project:
                project.business_requirements = json.dumps(brd)
                self.db.commit()
                
        self.log(
            project_id, 
            "Business Requirement Document (BRD) created. Success metrics and goals mapped.", 
            log_type="artifact", 
            payload=brd
        )
        
        return state
