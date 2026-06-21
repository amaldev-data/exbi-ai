import json
import pandas as pd
import numpy as np
from backend.agents.base import BaseAgent

class KPIArchitectAgent(BaseAgent):
    def __init__(self, llm_service, db_session=None):
        super().__init__("KPI Architect Agent", llm_service, db_session)

    def run(self, state: dict) -> dict:
        project_id = state["project_id"]
        domain = state["business_discovery"].get("business_domain", "Sales")
        mappings = state["semantic_mappings"]
        cleaned_csv_path = state["cleaned_csv_path"]
        
        self.log(project_id, f"Architecting custom {domain} Key Performance Indicators (KPIs)...", log_type="system")
        
        # Load cleaned data to calculate actual KPI values
        df = pd.read_csv(cleaned_csv_path)
        
        prompt = f"""
        Architect a KPI Dashboard layout for a {domain} dataset.
        Available columns: {df.columns.tolist()}
        Semantic mappings: {json.dumps(mappings)}
        
        Recommend 3 high-impact KPIs to track. For each KPI, specify:
        1. "id": A string id (e.g. "total_revenue").
        2. "title": A professional label (e.g. "Total Gross Revenue").
        3. "column": The actual column in the dataset to aggregate (e.g. "Amount" or "MonthlyIncome").
        4. "formula": Aggregation formula (e.g. "SUM", "AVERAGE", "COUNT", "RATIO").
        5. "description": Contextual explanation of the business value.
        
        Return strictly JSON list of objects.
        """
        
        system_prompt = "You are the KPI Architect Agent. Recommend and structure dataset KPIs in JSON format."
        response_str = self.llm_service.query(prompt, system_prompt, json_mode=True)
        
        try:
            kpis_spec = json.loads(response_str)
            if not isinstance(kpis_spec, list) or len(kpis_spec) == 0:
                raise KeyError("Invalid KPI spec structure")
        except Exception:
            # Fallback KPI specification based on domain
            domain_lower = domain.lower()
            if "hr" in domain_lower or "employee" in domain_lower:
                kpis_spec = [
                    {"id": "headcount", "title": "Total Employees", "column": df.columns[0], "formula": "COUNT", "description": "Total active workforce census count."},
                    {"id": "avg_income", "title": "Average Monthly Income", "column": "MonthlyIncome" if "MonthlyIncome" in df.columns else df.columns[-1], "formula": "AVERAGE", "description": "Average salary across all active workers."},
                    {"id": "attrition_rate", "title": "Attrition Count", "column": "Attrition" if "Attrition" in df.columns else df.columns[0], "formula": "COUNT", "description": "Total employee turnover volume."}
                ]
            else:
                kpis_spec = [
                    {"id": "total_revenue", "title": "Total Gross Sales", "column": "Amount" if "Amount" in df.columns else df.columns[-1], "formula": "SUM", "description": "Cumulative total billing revenue across segments."},
                    {"id": "avg_order", "title": "Average Transaction Value", "column": "Amount" if "Amount" in df.columns else df.columns[-1], "formula": "AVERAGE", "description": "Mean value generated per billing invoice."},
                    {"id": "transaction_count", "title": "Total Order Volume", "column": df.columns[0], "formula": "COUNT", "description": "Aggregate volume of invoices processed."}
                ]
                
        # Calculate actual values for each KPI
        kpis_calculated = []
        for spec in kpis_spec:
            col = spec.get("column")
            formula = spec.get("formula")
            title = spec.get("title", "Metric")
            description = spec.get("description", "")
            val_formatted = "N/A"
            
            if col and col in df.columns:
                try:
                    if formula == "SUM":
                        val_formatted = f"${df[col].sum():,.2f}"
                    elif formula == "AVERAGE":
                        val_formatted = f"${df[col].mean():,.2f}"
                    elif formula == "COUNT":
                        # If counting attrition Yes
                        if col == "Attrition" and "Yes" in df[col].values:
                            val_formatted = str((df[col] == "Yes").sum())
                        else:
                            val_formatted = f"{len(df):,}"
                    else:
                        val_formatted = f"{df[col].mean():.2f}"
                except Exception:
                    val_formatted = "N/A"
                    
            kpis_calculated.append({
                "title": title,
                "value": val_formatted,
                "description": description
            })
            
        state["kpis"] = kpis_calculated
        
        self.log(
            project_id, 
            f"Calculated target metrics for {len(kpis_calculated)} KPI Architect specifications.", 
            log_type="artifact", 
            payload=kpis_calculated
        )
        
        return state
