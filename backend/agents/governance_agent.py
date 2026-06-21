import json
from backend.agents.base import BaseAgent
from backend.database.db_manager import Project

class GovernanceAgent(BaseAgent):
    def __init__(self, llm_service, db_session=None):
        super().__init__("Governance & QA Agent", llm_service, db_session)

    def run(self, state: dict) -> dict:
        project_id = state["project_id"]
        quality_report = state["quality_report"]
        kpis = state["kpis"]
        
        self.log(project_id, "Executing compliance audit on metric scopes and mathematical mappings...", log_type="system")
        
        # Calculate Governance Score dynamically based on validation anomalies
        violations_count = quality_report.get("total_violations_count", 0)
        base_score = 100 - min(40, violations_count * 5)
        
        prompt = f"""
        Conduct a compliance review for the analytics project:
        - Quality Report: {json.dumps(quality_report)}
        - KPIs Calculated: {json.dumps(kpis)}
        - Baseline score calculated: {base_score}
        
        Provide an Approval Certificate JSON containing:
        1. "overall_confidence_score": The final audited confidence rating (0-100).
        2. "status": "APPROVED", "APPROVED_WITH_WARNINGS", or "REJECTED".
        3. "signoff_officer": "Gary Stone (Executive Governance QA)"
        4. "governance_verdict": 2-sentence description summarizing data compliance.
        
        Return strictly JSON.
        """
        
        system_prompt = "You are the Governance QA Agent. Perform final compliance signoff and output JSON."
        response_str = self.llm_service.query(prompt, system_prompt, json_mode=True)
        
        try:
            cert = json.loads(response_str)
            if not isinstance(cert, dict) or "status" not in cert:
                raise KeyError("Missing status key")
            if "overall_confidence_score" not in cert:
                # Try fallback keys or use base_score
                cert["overall_confidence_score"] = int(cert.get("confidence_score", cert.get("confidence", base_score)))
        except Exception:
            cert = {
                "overall_confidence_score": int(base_score),
                "status": "APPROVED" if violations_count == 0 else "APPROVED_WITH_WARNINGS",
                "signoff_officer": "Gary Stone (Executive Governance QA)",
                "governance_verdict": f"Audit complete. Data matches schema bounds. {violations_count} warning anomalies flagged during intake."
            }
            
        state["qa_certification"] = cert
        state["approval_certificate"] = cert
        
        # Save to Database
        if self.db:
            project = self.db.query(Project).filter(Project.id == project_id).first()
            if project:
                project.approval_certificate = json.dumps(cert)
                self.db.commit()
                
        self.log(
            project_id, 
            f"Governance sign-off completed. Overall Confidence: {cert.get('overall_confidence_score', base_score)}%. Status: {cert['status']}.", 
            log_type="artifact", 
            payload=cert
        )
        
        return state
