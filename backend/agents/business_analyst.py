import json
from backend.agents.base import BaseAgent

class BusinessAnalystAgent(BaseAgent):
    def __init__(self, llm_service, db_session=None):
        super().__init__("Business Analyst Agent", llm_service, db_session)

    def run(self, state: dict) -> dict:
        project_id = state["project_id"]
        dataset_info = state["dataset_info"]
        domain = dataset_info["business_discovery"]["business_domain"]
        
        self.log(project_id, f"Business Analyst Agent identifying strategic analytical targets for domain: {domain}...", log_type="system")
        
        prompt = f"""
        Given the detected business domain '{domain}' and this dataset info:
        {json.dumps(dataset_info)}
        
        Recommend a list of 5 to 8 specific analytical target options for the user.
        Each option must be relevant and structured with:
        - "id": a short snake_case identifier (e.g., "revenue_analysis", "employee_demographics")
        - "title": a user-friendly label (e.g., "Revenue & Trend Analysis")
        - "description": a brief explanation of what the analysis entails
        - "recommended": true/false (mark true if highly relevant to this domain)
        - "reason": brief explanation why it is recommended
        
        Return a JSON response with an "options" list of these items.
        Return strictly JSON.
        """
        
        system_prompt = "You are the Business Analyst Agent. Suggest relevant analyses for a dataset."
        response_str = self.llm_service.query(prompt, system_prompt, json_mode=True)
        
        try:
            opts = json.loads(response_str)
            if not isinstance(opts, dict) or "options" not in opts:
                raise KeyError()
            options = opts["options"]
        except Exception:
            # Fallback based on domain
            domain_lower = domain.lower()
            if "sales" in domain_lower or "revenue" in domain_lower:
                options = [
                    {"id": "revenue_trend", "title": "Revenue & Trend Analysis", "description": "Examine overall revenue trajectories and seasonality.", "recommended": True, "reason": "Essential for tracking revenue growth."},
                    {"id": "product_performance", "title": "Product Sales Analysis", "description": "Identify best-selling product categories and units.", "recommended": True, "reason": "Highlights key margin drivers."},
                    {"id": "regional_sales", "title": "Regional Performance Analysis", "description": "Map sales and volume across geographical areas.", "recommended": True, "reason": "Shows highest growth opportunities."},
                    {"id": "customer_purchasing", "title": "Customer Purchase Segmentation", "description": "Analyze average ticket size and customer distribution.", "recommended": False, "reason": "Useful for secondary customer insights."},
                    {"id": "executive_summary", "title": "Executive Summary Dashboard", "description": "Get high-level KPI cards and trend overviews.", "recommended": True, "reason": "Recommended for senior leadership reviews."},
                    {"id": "business_report", "title": "Business Report", "description": "Generate a comprehensive business-focused text report.", "recommended": True, "reason": "Recommended for offline reading and audit trails."}
                ]
            elif "human" in domain_lower or "hr" in domain_lower:
                options = [
                    {"id": "attrition_drivers", "title": "Employee Attrition Analysis", "description": "Pinpoint indicators and demographics linked to turnover.", "recommended": True, "reason": "Critical for retention strategy."},
                    {"id": "compensation_parity", "title": "Compensation & Income Breakdown", "description": "Inspect salary ranges across roles, departments, and age groups.", "recommended": True, "reason": "Ensures equity and budget control."},
                    {"id": "department_performance", "title": "Department Performance Comparison", "description": "Compare tenure and headcount distribution across divisions.", "recommended": True, "reason": "Identifies workforce imbalances."},
                    {"id": "tenure_survival", "title": "Tenure & Loyalty Mapping", "description": "Model how long employees stay in relation to variables.", "recommended": False, "reason": "Helps predict future hiring needs."},
                    {"id": "executive_summary", "title": "Executive Summary Dashboard", "description": "Get high-level KPI cards and trend overviews.", "recommended": True, "reason": "Recommended for senior leadership reviews."},
                    {"id": "business_report", "title": "Business Report", "description": "Generate a comprehensive business-focused text report.", "recommended": True, "reason": "Recommended for offline reading and audit trails."}
                ]
            elif "churn" in domain_lower or "customer" in domain_lower:
                options = [
                    {"id": "churn_risk", "title": "Customer Churn Risk Analysis", "description": "Analyze churn rates and drivers (contract types, charges).", "recommended": True, "reason": "Top priority for retention plans."},
                    {"id": "charges_distribution", "title": "Monthly Charges Distribution", "description": "Examine billing clusters and identify cost-sensitive customer brackets.", "recommended": True, "reason": "Helps customize pricing strategies."},
                    {"id": "tenure_retention", "title": "Customer Tenure Cohorts", "description": "Track retention rates over time from sign-up.", "recommended": True, "reason": "Maps customer lifecycle metrics."},
                    {"id": "executive_summary", "title": "Executive Summary Dashboard", "description": "Get high-level KPI cards and trend overviews.", "recommended": True, "reason": "Recommended for senior leadership reviews."},
                    {"id": "business_report", "title": "Business Report", "description": "Generate a comprehensive business-focused text report.", "recommended": True, "reason": "Recommended for offline reading and audit trails."}
                ]
            else:
                options = [
                    {"id": "performance_metrics", "title": "Operations Performance Analysis", "description": "Summarize statistical distributions and core operations trends.", "recommended": True, "reason": "Essential operational overview."},
                    {"id": "correlation_matrix", "title": "Variable Correlation Mapping", "description": "Examine Pearson coefficients across numeric variables.", "recommended": True, "reason": "Flags hidden linear relationships."},
                    {"id": "outlier_flagging", "title": "Outlier and Extreme Value Flagging", "description": "Isolate extreme values and identify recording errors.", "recommended": False, "reason": "Useful for secondary data audit audits."},
                    {"id": "executive_summary", "title": "Executive Summary Dashboard", "description": "Get high-level KPI cards and trend overviews.", "recommended": True, "reason": "Recommended for senior leadership reviews."},
                    {"id": "business_report", "title": "Business Report", "description": "Generate a comprehensive business-focused text report.", "recommended": True, "reason": "Recommended for offline reading and audit trails."}
                ]
                
        state["recommendations"] = options
        self.log(project_id, f"Business Analyst generated {len(options)} analysis recommendations.", log_type="system")
        return state

    def run_analysis_mapping(self, state: dict) -> dict:
        project_id = state["project_id"]
        dataset_info = state["dataset_info"]
        selected_analyses = state.get("selected_analyses", [])
        profile = state.get("profile", dataset_info["technical_profile"])
        domain = dataset_info["business_discovery"]["business_domain"]
        
        self.log(project_id, "Business Analyst mapping selected requirements to Business Question Framework...", log_type="system")
        
        columns = profile.get("column_names", [])
        classifications = profile.get("column_classifications", {})
        relationships = profile.get("relationships", [])
        
        # Build programmatic fallback first
        fallback_framework = []
        used_pairs = set()
        
        for req in selected_analyses:
            req_lower = req.lower()
            mapped = False
            
            # Special case for correlation matrix/heatmap
            if "correlation" in req_lower:
                fallback_framework.append({
                    "business_question": "What is the correlation between all numerical variables?",
                    "x_col": None,
                    "y_col": None,
                    "chart_type": "heatmap",
                    "user_requirement": req
                })
                mapped = True
                continue
                
            # Try to find a relationship that matches this requirement
            for rel in relationships:
                x = rel["x_col"]
                y = rel["y_col"]
                x_type = rel["x_type"]
                y_type = rel["y_type"]
                pair = (x, y)
                
                if pair in used_pairs:
                    continue
                
                # Check for revenue/sales trends
                if ("revenue" in req_lower or "sales" in req_lower or "trend" in req_lower) and x_type == "Date" and any(k in y.lower() for k in ["amount", "revenue", "sales", "price"]):
                    fallback_framework.append({
                        "business_question": f"What are the {y} trends over time?",
                        "x_col": x,
                        "y_col": y,
                        "chart_type": "line",
                        "user_requirement": req
                    })
                    used_pairs.add(pair)
                    mapped = True
                    break
                    
                # Check for category / product performance
                elif ("product" in req_lower or "category" in req_lower or "performance" in req_lower) and x_type == "Categorical" and any(k in x.lower() for k in ["category", "product", "item"]) and any(k in y.lower() for k in ["amount", "revenue", "sales", "qty", "quantity"]):
                    unique_count = rel.get("unique_x_count", 0)
                    ctype = "bar" if unique_count <= 10 else "horizontalBar"
                    fallback_framework.append({
                        "business_question": f"Which {x} generates the highest {y}?",
                        "x_col": x,
                        "y_col": y,
                        "chart_type": ctype,
                        "user_requirement": req
                    })
                    used_pairs.add(pair)
                    mapped = True
                    break
                    
                # Check for regional sales
                elif ("region" in req_lower or "geo" in req_lower) and x_type == "Categorical" and any(k in x.lower() for k in ["region", "country", "state", "city"]) and any(k in y.lower() for k in ["amount", "revenue", "sales", "qty", "quantity"]):
                    fallback_framework.append({
                        "business_question": f"Which {x} performs best in terms of {y}?",
                        "x_col": x,
                        "y_col": y,
                        "chart_type": "bar",
                        "user_requirement": req
                    })
                    used_pairs.add(pair)
                    mapped = True
                    break

                # Check for compensation/income
                elif ("compensation" in req_lower or "salary" in req_lower or "income" in req_lower) and x_type == "Categorical" and any(k in x.lower() for k in ["department", "role", "title"]) and any(k in y.lower() for k in ["income", "salary", "pay"]):
                    fallback_framework.append({
                        "business_question": f"What is the average {y} by {x}?",
                        "x_col": x,
                        "y_col": y,
                        "chart_type": "bar",
                        "user_requirement": req
                    })
                    used_pairs.add(pair)
                    mapped = True
                    break

                # Check for attrition/churn drivers
                elif ("attrition" in req_lower or "churn" in req_lower) and x_type in ["Categorical", "Boolean"] and any(k in x.lower() for k in ["attrition", "churn"]) and any(k in y.lower() for k in ["income", "salary", "age", "tenure"]):
                    fallback_framework.append({
                        "business_question": f"How does {x} relate to employee {y}?",
                        "x_col": x,
                        "y_col": y,
                        "chart_type": "bar",
                        "user_requirement": req
                    })
                    used_pairs.add(pair)
                    mapped = True
                    break

            if not mapped:
                # Fallback: Just grab any unused relationship
                for rel in relationships:
                    x = rel["x_col"]
                    y = rel["y_col"]
                    x_type = rel["x_type"]
                    y_type = rel["y_type"]
                    pair = (x, y)
                    if pair not in used_pairs:
                        ctype = "line" if x_type == "Date" else "bar"
                        if x_type == "Categorical":
                            unique_count = rel.get("unique_x_count", 0)
                            if unique_count > 10:
                                ctype = "horizontalBar"
                        fallback_framework.append({
                            "business_question": f"Analysis of {y} relative to {x}",
                            "x_col": x,
                            "y_col": y,
                            "chart_type": ctype,
                            "user_requirement": req
                        })
                        used_pairs.add(pair)
                        mapped = True
                        break

        # Query LLM to generate the Business Question Framework
        prompt = f"""
        Given the detected business domain '{domain}' and this dataset info:
        - Columns: {json.dumps(columns)}
        - Classifications: {json.dumps(classifications)}
        - Discovered Relationships: {json.dumps(relationships)}
        - Selected Requirements: {json.dumps(selected_analyses)}
        
        Map the selected requirements to a list of business questions (the "Business Question Framework").
        
        For each business question, specify:
        - "business_question": A clear, executive business question (e.g. "Which region generates the highest revenue?")
        - "x_col": The independent variable column from the dataset relationships.
        - "y_col": The dependent variable column from the dataset relationships (or null if not applicable).
        - "chart_type": The exact chart type based on the Playbook Chart Selection Matrix:
          - Date + Numerical -> "line"
          - Categorical + Numerical -> "bar" (or "horizontalBar" if category unique counts > 10)
          - Category distribution (unique counts <= 10) -> "pie"
          - Category distribution (unique counts > 10) -> "horizontalBar"
          - Numerical + Numerical -> "scatter"
          - Multiple Numerical -> "heatmap"
        - "user_requirement": The requirement/analysis ID this question maps to.
        
        Rules:
        1. Every question must use actual columns from the discovered relationships.
        2. Never use Identifier columns in any business question, x_col, or y_col.
        3. Do not map duplicate (X, Y) column pairs.
        
        Return a JSON response with a key "business_question_framework" containing the list.
        Return strictly JSON.
        """
        
        system_prompt = "You are the Business Analyst Agent. Map user requirements to a structured Business Question Framework."
        response_str = self.llm_service.query(prompt, system_prompt, json_mode=True)
        
        try:
            framework_data = json.loads(response_str)
            if not isinstance(framework_data, dict) or "business_question_framework" not in framework_data:
                raise KeyError()
            framework = framework_data["business_question_framework"]
            
            # Basic validation on LLM output
            validated_framework = []
            seen = set()
            for q in framework:
                x = q.get("x_col")
                y = q.get("y_col")
                if x in columns and (y is None or y in columns):
                    # Check classifications to avoid Identifier
                    if classifications.get(x) == "Identifier" or classifications.get(y) == "Identifier":
                        continue
                    pair = (x, y)
                    if pair not in seen:
                        seen.add(pair)
                        validated_framework.append(q)
            if len(validated_framework) > 0:
                state["business_question_framework"] = validated_framework
            else:
                state["business_question_framework"] = fallback_framework
        except Exception:
            state["business_question_framework"] = fallback_framework
            
        self.log(project_id, f"Business Analyst mapped requirements to {len(state['business_question_framework'])} business questions.", log_type="system")
        return state
