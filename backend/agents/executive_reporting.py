import json
from backend.agents.base import BaseAgent
from backend.database.db_manager import Project

class ExecutiveReportingAgent(BaseAgent):
    def __init__(self, llm_service, db_session=None):
        super().__init__("Executive Reporting Agent", llm_service, db_session)

    def run(self, state: dict) -> dict:
        project_id = state["project_id"]
        brd = state["business_requirements"]
        strategy = state["analytics_strategy"]
        profile = state["profile"]
        insights = state["insights"]
        cert = state["approval_certificate"]
        
        self.log(project_id, "Compiling final consulting-grade Executive Report document...", log_type="system")
        
        prompt = f"""
        Draft a comprehensive, consulting-grade executive report. Use the provided details:
        - Requirements Document: {json.dumps(brd)}
        - Execution Strategy: {json.dumps(strategy)}
        - Data Profiling: {json.dumps(profile)}
        - Discovered Insights: {json.dumps(insights)}
        - Governance Status: {json.dumps(cert)}
        
        Your output should be a professional markdown report with the following exact section headers:
        ## Executive Summary
        Provide a 2-paragraph overview of findings and objectives.
        
        ## Dataset Overview
        Briefly describe the row count, features, and columns.
        
        ## Methodology
        Explain the cleaning and analytical process.
        
        ## Data Quality Assessment
        Highlight missing value densities and outlier detections.
        
        ## Key Findings
        Integrate the discovered insights. Format with bullet points.
        
        ## Business Recommendations
        Detail the strategic recommendations and action plan.
        
        Output only the markdown. Avoid conversational introductory text.
        """
        
        system_prompt = "You are the Executive Reporting Agent. Compile a print-ready markdown consulting report."
        response_str = self.llm_service.query(prompt, system_prompt, json_mode=False)
        
        # Ensure we have the headers if the model returned something else
        if "## Executive Summary" not in response_str:
            # Fallback markdown report
            insights_list = ""
            for item in insights:
                insights_list += f"* **Finding**: {item['finding']}\n  - **Risk**: {item['risk']}\n  - **Action**: {item['action']} (Confidence: {item['confidence_score']}%)\n"
                
            response_str = f"""
## Executive Summary
This executive analytics summary addresses the core stakeholder objectives and decisions outlined during dataset discovery. Our agentic departments have cleansed, profiled, mapped, and audited the uploaded dataset, compiling these strategic insights to maximize operational yield.

## Dataset Overview
The dataset contains a total of {profile['rows']} rows and {profile['columns']} columns. The technical profile indicates a distribution across dimensions and numeric metrics.

## Methodology
Data was loaded, validated, and processed using standard pandas cleansing. The semantic engine mapped column categories to metrics, dimensions, time series, and customer boundaries.

## Data Quality Assessment
Prior to analysis, the dataset scored {profile['quality_score']}/100 on structural integrity. Missing data was median-imputed, casing was standardized, and whitespace noise was cleared.

## Key Findings
{insights_list}

## Business Recommendations
Based on these findings, we recommend:
1. Focus resource distribution on high-performing categories.
2. Investigate high-risk cohorts displaying performance variances.
3. Establish regular KPI review cycles to track MOM growth.
"""

        state["report_markdown"] = response_str
        
        # Save to Database
        if self.db:
            project = self.db.query(Project).filter(Project.id == project_id).first()
            if project:
                project.executive_report = response_str
                self.db.commit()
                
        self.log(
            project_id, 
            "Executive Report text compiled and saved. Ready for final PDF/Word generation.", 
            log_type="artifact", 
            payload={"report_markdown": response_str}
        )
        
        return state
