import json
from backend.agents.base import BaseAgent
from backend.database.db_manager import Project

class DashboardArchitectAgent(BaseAgent):
    def __init__(self, llm_service, db_session=None):
        super().__init__("Dashboard Architect Agent", llm_service, db_session)

    def run(self, state: dict) -> dict:
        project_id = state["project_id"]
        domain = state["business_discovery"].get("business_domain", "Sales")
        mappings = state["semantic_mappings"]
        kpis = state["kpis"]
        user_inputs = state.get("user_inputs", {})
        audience = user_inputs.get("audience", "Executive Leadership")
        
        self.log(project_id, f"Designing dashboard layout grid for audience: {audience}...", log_type="system")
        
        prompt = f"""
        Design a professional Dashboard Architecture JSON for a {domain} dataset.
        Audience: {audience}
        KPIs: {json.dumps(kpis)}
        Semantic Mappings: {json.dumps(mappings)}
        
        Tailor the layout structure to:
        1. "audience_theme": Summary of the dashboard focus for this role.
        2. "layout_grid": List of chart definitions. Recommend 3 chart structures:
           - "type": "line", "bar", or "doughnut".
           - "title": Descriptive title.
           - "id": unique string id (e.g. "monthly_revenue").
           - "xAxis": Mapped date or dimension column.
           - "yAxis": Mapped numeric metric column.
           - "description": Rationale for this chart.
           
        Return strictly JSON.
        """
        
        system_prompt = "You are the Dashboard Architect Agent. Output grid blueprint in JSON format."
        response_str = self.llm_service.query(prompt, system_prompt, json_mode=True)
        
        try:
            blueprint = json.loads(response_str)
            if not isinstance(blueprint, dict) or "layout_grid" not in blueprint:
                raise KeyError("Missing layout_grid key")
        except Exception:
            # Fallback layout grid
            metric_col = mappings["metrics"][0] if len(mappings["metrics"]) > 0 else "Amount"
            dim_col = mappings["dimensions"][0] if len(mappings["dimensions"]) > 0 else "Category"
            date_col = mappings["date_columns"][0] if len(mappings["date_columns"]) > 0 else "Date"
            
            blueprint = {
                "audience_theme": f"Strategic dashboard for {audience} with focus on performance distribution.",
                "layout_grid": [
                    {
                        "type": "line",
                        "title": f"{metric_col} Performance Trend",
                        "id": "line_trend",
                        "xAxis": date_col,
                        "yAxis": metric_col,
                        "description": "Chronological performance trend overview."
                    },
                    {
                        "type": "bar",
                        "title": f"Mean {metric_col} by {dim_col}",
                        "id": "category_bar",
                        "xAxis": dim_col,
                        "yAxis": metric_col,
                        "description": "Category performance comparison."
                    },
                    {
                        "type": "doughnut",
                        "title": "Segment Proportions",
                        "id": "segment_doughnut",
                        "xAxis": dim_col,
                        "yAxis": metric_col,
                        "description": "Distribution proportions across key cohorts."
                    }
                ]
            }
            
        state["dashboard_blueprint"] = blueprint
        
        self.log(
            project_id, 
            f"Dashboard architecture finalized. Designed {len(blueprint['layout_grid'])} components for {audience}.", 
            log_type="artifact", 
            payload=blueprint
        )
        
        return state
