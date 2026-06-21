import os
import json
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg') # Headless mode for server environment
import matplotlib.pyplot as plt
from backend.config import TEMP_UPLOADS

class DataEngine:
    def __init__(self, upload_dir=None):
        self.upload_dir = upload_dir or TEMP_UPLOADS
        os.makedirs(self.upload_dir, exist_ok=True)

    def load_dataset(self, file_path: str) -> pd.DataFrame:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.csv':
            return pd.read_csv(file_path)
        elif ext in ['.xlsx', '.xls']:
            return pd.read_excel(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    def classify_columns(self, df: pd.DataFrame) -> dict:
        classifications = {}
        for col in df.columns:
            col_lower = col.lower()
            unique_ratio = df[col].nunique() / max(1, len(df))
            
            # Identifier
            is_id_name = any(k in col_lower for k in ["id", "key", "code", "no", "num", "identifier"]) or col_lower in ["uuid", "index", "customer_id", "order_id", "invoice_id", "employee_id", "transaction_id"]
            is_float = df[col].dtype in [np.float64, np.float32]
            is_id = is_id_name and (unique_ratio > 0.8 or df[col].dtype == object or col_lower in ["employee_id", "customerid", "customer_id", "id", "index", "uuid"]) and not is_float
            
            # Boolean
            is_bool = (df[col].dtype == bool or 
                       (df[col].nunique() == 2 and any(str(val).lower() in ["true", "false", "yes", "no", "1", "0"] for val in df[col].dropna().unique())))
            
            # Date
            is_date = "date" in col_lower or "time" in col_lower or "timestamp" in col_lower
            if not is_date and df[col].dtype == object:
                non_null_samples = df[col].dropna().head(10).astype(str)
                if len(non_null_samples) > 0:
                    import re
                    date_matches = sum(1 for val in non_null_samples if re.match(r'^\d{4}[-/]\d{1,2}[-/]\d{1,2}$', val) or re.match(r'^\d{1,2}[-/]\d{1,2}[-/]\d{4}$', val))
                    if date_matches / len(non_null_samples) >= 0.8:
                        is_date = True
            
            # Numerical
            is_numeric = (df[col].dtype in [np.int64, np.float64, np.int32, np.float32] or pd.api.types.is_numeric_dtype(df[col])) and not is_id
            
            # Text
            is_text = False
            if df[col].dtype == object and not is_id and not is_bool and not is_date:
                non_null_vals = df[col].dropna()
                if len(non_null_vals) > 0:
                    avg_len = non_null_vals.astype(str).str.len().mean()
                    if avg_len > 20 and (non_null_vals.nunique() > 10 or unique_ratio > 0.5):
                        is_text = True
            
            if is_id:
                classifications[col] = "Identifier"
            elif is_bool:
                classifications[col] = "Boolean"
            elif is_date:
                classifications[col] = "Date"
            elif is_numeric:
                classifications[col] = "Numerical"
            elif is_text:
                classifications[col] = "Text"
            else:
                classifications[col] = "Categorical"
        return classifications

    def discover_relationships(self, df: pd.DataFrame, classifications: dict) -> list:
        relationships = []
        for x_col in df.columns:
            x_type = classifications[x_col]
            if x_type in ["Date", "Categorical", "Boolean"]:
                for y_col in df.columns:
                    y_type = classifications[y_col]
                    if y_type == "Numerical" and classifications[y_col] != "Identifier":
                        relationships.append({
                            "x_col": x_col,
                            "y_col": y_col,
                            "x_type": x_type,
                            "y_type": y_type,
                            "unique_x_count": int(df[x_col].nunique())
                        })
        return relationships

    def get_valid_charts_spec(self, df: pd.DataFrame, classifications: dict) -> list:
        dates = [col for col, cls in classifications.items() if cls == "Date"]
        numerics = [col for col, cls in classifications.items() if cls == "Numerical"]
        categoricals = [col for col, cls in classifications.items() if cls == "Categorical"]
        booleans = [col for col, cls in classifications.items() if cls == "Boolean"]
        
        charts_to_generate = []
        
        # 1. Date + Numerical -> Trend Line Chart
        for date_col in dates:
            for num_col in numerics[:2]:
                charts_to_generate.append({
                    "id": f"trend_{date_col}_{num_col}",
                    "type": "line",
                    "x_col": date_col,
                    "y_col": num_col,
                    "title": f"{num_col} Trend Over Time",
                    "description": f"Analysis of {num_col} trends chronologically across {date_col}."
                })
                
        # 2. Categorical + Numerical -> Bar Chart
        for cat_col in categoricals[:2]:
            for num_col in numerics[:2]:
                charts_to_generate.append({
                    "id": f"bar_{cat_col}_{num_col}",
                    "type": "bar",
                    "x_col": cat_col,
                    "y_col": num_col,
                    "title": f"Total {num_col} by {cat_col}",
                    "description": f"Comparison of cumulative {num_col} performance across {cat_col} segments."
                })
                
        # 3. Category Distribution -> Pie Chart
        for cat_col in (categoricals + booleans)[:2]:
            unique_count = df[cat_col].nunique()
            if 1 < unique_count <= 10:
                charts_to_generate.append({
                    "id": f"pie_{cat_col}",
                    "type": "pie",
                    "x_col": cat_col,
                    "y_col": None,
                    "title": f"Distribution by {cat_col}",
                    "description": f"Segment share breakdown for {cat_col} categories."
                })
                
        # 4. Numerical + Numerical -> Scatter Plot
        if len(numerics) >= 2:
            charts_to_generate.append({
                "id": f"scatter_{numerics[0]}_{numerics[1]}",
                "type": "scatter",
                "x_col": numerics[0],
                "y_col": numerics[1],
                "title": f"{numerics[0]} vs {numerics[1]} Correlation",
                "description": f"Statistical dispersion mapping of {numerics[0]} against {numerics[1]}."
            })
            
        # 5. Multiple Numerical Variables -> Correlation Heatmap
        if len(numerics) >= 3:
            charts_to_generate.append({
                "id": "correlation_heatmap",
                "type": "heatmap",
                "x_col": None,
                "y_col": None,
                "title": "Variable Correlation Matrix",
                "description": "Pearson correlation coefficient heatmap showing relationships between all numeric variables."
            })
            
        return charts_to_generate[:4]

    def profile_dataset(self, df: pd.DataFrame) -> dict:
        row_count, col_count = df.shape
        columns = df.columns.tolist()
        
        # Detect datatypes
        dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}
        
        # Missing values
        missing_values = {col: int(count) for col, count in df.isnull().sum().items()}
        total_missing = sum(missing_values.values())
        
        # Duplicates
        duplicate_count = int(df.duplicated().sum())
        
        # Classify column roles with semantic profiling
        date_cols = []
        numeric_cols = []
        categorical_cols = []
        primary_keys = []
        foreign_keys = []
        target_variables = []
        geographical_fields = []
        currency_fields = []
        percentage_fields = []
        
        # 1. Date Detection & Semantic Classification
        for col in columns:
            col_lower = col.lower()
            is_date = "date" in col_lower or "time" in col_lower or "timestamp" in col_lower or "year" in col_lower or "month" in col_lower or "day" in col_lower
            if is_date:
                # Exclude numerical financial metrics containing 'monthly' or 'daily' (e.g. MonthlyIncome, MonthlyCharges)
                financial_keys = ["income", "charge", "salary", "revenue", "sales", "spend", "cost", "amount", "bill", "payment"]
                if any(fk in col_lower for fk in financial_keys):
                    is_date = False
            
            # Check values if it's a string column
            if not is_date and df[col].dtype == object:
                non_null_samples = df[col].dropna().head(10).astype(str)
                if len(non_null_samples) > 0:
                    date_matches = 0
                    for val in non_null_samples:
                        import re
                        if re.match(r'^\d{4}[-/]\d{1,2}[-/]\d{1,2}$', val) or re.match(r'^\d{1,2}[-/]\d{1,2}[-/]\d{4}$', val):
                            date_matches += 1
                    if date_matches / len(non_null_samples) >= 0.8:
                        is_date = True
            
            if is_date:
                date_cols.append(col)
            elif pd.api.types.is_numeric_dtype(df[col]):
                numeric_cols.append(col)
            else:
                categorical_cols.append(col)
                
        # 2. Key, Currency, Geographic, Percentage, Target classification
        for col in columns:
            col_lower = col.lower()
            
            # Primary / Foreign Keys
            is_id_name = any(k in col_lower for k in ["id", "key", "code", "no", "num", "identifier"])
            if is_id_name:
                unique_ratio = df[col].nunique() / max(1, row_count)
                if unique_ratio > 0.95 and df[col].nunique() > 1:
                    primary_keys.append(col)
                else:
                    foreign_keys.append(col)
            
            # Currency Fields
            is_financial_name = any(k in col_lower for k in ["amount", "revenue", "sales", "income", "turnover", "price", "cost", "salary", "charge", "bill", "payment", "spend", "budget", "profit", "margin", "tax", "fee"])
            if is_financial_name and col in numeric_cols:
                currency_fields.append(col)
            
            # Percentage Fields
            is_percentage_name = any(k in col_lower for k in ["rate", "ratio", "pct", "percent", "percentage", "share", "margin"])
            if is_percentage_name and col in numeric_cols:
                sample_vals = df[col].dropna()
                if len(sample_vals) > 0:
                    is_fractional = sample_vals.between(0, 1.05).all()
                    is_pct_scale = sample_vals.between(0, 105).all() and sample_vals.max() > 1.5
                    if is_fractional or is_pct_scale:
                        percentage_fields.append(col)
            
            # Geographical Fields
            is_geo_name = any(k in col_lower for k in ["region", "country", "state", "city", "zip", "lat", "long", "address", "postal", "county", "province", "territory", "location"])
            if is_geo_name:
                geographical_fields.append(col)
                
            # Target Variables
            is_target_name = any(k in col_lower for k in ["attrition", "churn", "status", "label", "class", "target", "y", "outcome", "default", "fraud", "click", "conversion", "satisfaction", "rating"])
            if is_target_name:
                target_variables.append(col)
                
        # 3. Time Series Structures Detection
        time_series_structure = None
        if len(date_cols) > 0:
            primary_date = date_cols[0]
            try:
                temp_dates = pd.to_datetime(df[primary_date], errors='coerce').dropna()
                if len(temp_dates) > 1:
                    is_sorted = temp_dates.is_monotonic_increasing
                    # Check step frequency
                    time_diffs = temp_dates.diff().dropna().dt.days.value_counts()
                    if len(time_diffs) > 0:
                        most_common_diff = time_diffs.index[0]
                        freq_label = "Daily" if most_common_diff == 1 else "Weekly" if most_common_diff == 7 else "Monthly" if 28 <= most_common_diff <= 31 else "Irregular"
                        time_series_structure = {
                            "date_column": primary_date,
                            "is_chronologically_sorted": bool(is_sorted),
                            "estimated_frequency": freq_label,
                            "min_date": str(temp_dates.min().strftime('%Y-%m-%d')),
                            "max_date": str(temp_dates.max().strftime('%Y-%m-%d'))
                        }
            except Exception:
                pass
                
        # 4. Derived Metrics suggestions
        derived_suggestions = []
        if len(currency_fields) >= 2:
            derived_suggestions.append({
                "metric_name": "Cost-to-Revenue Ratio",
                "formula": "Cost / Revenue",
                "rationale": "Financial performance ratio analysis."
            })
        if len(currency_fields) >= 1 and "Quantity" in columns:
            derived_suggestions.append({
                "metric_name": "Average Unit Price",
                "formula": f"{currency_fields[0]} / Quantity",
                "rationale": "Unit economics calculation."
            })

        # Statistical summary
        desc = df.describe(include=[np.number]).to_dict() if len(numeric_cols) > 0 else {}
        stats_summary = {}
        for col, s in desc.items():
            stats_summary[col] = {
                "mean": float(s.get("mean", 0)),
                "min": float(s.get("min", 0)),
                "max": float(s.get("max", 0)),
                "median": float(s.get("50%", 0))
            }

        # Data quality score calculation
        quality_score = 100
        if row_count > 0:
            missing_ratio = total_missing / (row_count * col_count)
            dup_ratio = duplicate_count / row_count
            quality_score -= int(missing_ratio * 40 + dup_ratio * 30)
            quality_score = max(50, min(100, quality_score))

        classifications = self.classify_columns(df)
        relationships = self.discover_relationships(df, classifications)

        return {
            "rows": row_count,
            "columns": col_count,
            "column_names": columns,
            "data_types": dtypes,
            "missing_values": missing_values,
            "total_missing": total_missing,
            "duplicate_count": duplicate_count,
            "date_columns": date_cols,
            "numeric_columns": numeric_cols,
            "categorical_columns": categorical_cols,
            "primary_keys": primary_keys,
            "foreign_keys": foreign_keys,
            "target_variables": target_variables,
            "geographical_fields": geographical_fields,
            "currency_fields": currency_fields,
            "percentage_fields": percentage_fields,
            "time_series_structure": time_series_structure,
            "derived_suggestions": derived_suggestions,
            "stats_summary": stats_summary,
            "quality_score": quality_score,
            "column_classifications": classifications,
            "relationships": relationships
        }

    def clean_dataset(self, df: pd.DataFrame, profile: dict) -> pd.DataFrame:
        df_cleaned = df.copy()
        
        # 1. Remove duplicates
        df_cleaned = df_cleaned.drop_duplicates()
        
        # 2. Impute missing values
        for col in df_cleaned.columns:
            if df_cleaned[col].isnull().sum() > 0:
                if col in profile["numeric_columns"]:
                    # Fill missing numerics with median
                    median_val = df_cleaned[col].median()
                    df_cleaned[col] = df_cleaned[col].fillna(median_val if pd.notnull(median_val) else 0)
                else:
                    # Fill missing categoricals with placeholder
                    df_cleaned[col] = df_cleaned[col].fillna("Unknown")

        # 3. Standardize text columns (strip whitespace, capitalize)
        for col in profile["categorical_columns"]:
            if df_cleaned[col].dtype == object:
                df_cleaned[col] = df_cleaned[col].astype(str).str.strip()

        # 4. Standardize dates
        for col in profile["date_columns"]:
            try:
                df_cleaned[col] = pd.to_datetime(df_cleaned[col], errors='coerce')
                # Format datetimes back to YYYY-MM-DD strings for clean representation
                df_cleaned[col] = df_cleaned[col].dt.strftime('%Y-%m-%d')
            except Exception:
                pass # Fallback if datetime coercion fails

        return df_cleaned

    def validate_business_rules(self, df: pd.DataFrame, profile: dict) -> dict:
        violations = []
        violation_count = 0
        
        # Rule 1: Numeric negatives check for commonly non-negative columns
        money_keys = ["sales", "revenue", "price", "amount", "quantity", "income", "charge"]
        for col in profile["numeric_columns"]:
            col_lower = col.lower()
            if any(k in col_lower for k in money_keys):
                negatives = df[df[col] < 0]
                if not negatives.empty:
                    neg_count = len(negatives)
                    violations.append({
                        "column": col,
                        "rule": "Non-negative values constraint",
                        "violation_desc": f"Found {neg_count} negative entries in '{col}'. Values must be >= 0.",
                        "severity": "WARNING"
                    })
                    violation_count += neg_count
                    
        # Rule 2: Outliers check (Z-Score > 3)
        for col in profile["numeric_columns"]:
            col_vals = df[col].dropna()
            if len(col_vals) > 5 and col_vals.std() > 0:
                z_scores = np.abs((col_vals - col_vals.mean()) / col_vals.std())
                outliers = z_scores[z_scores > 3]
                if not outliers.empty:
                    violations.append({
                        "column": col,
                        "rule": "Statistical outlier threshold",
                        "violation_desc": f"Found {len(outliers)} entries in '{col}' exceeding 3 standard deviations (outliers).",
                        "severity": "INFO"
                    })
                    
        return {
            "validation_passed": len([v for v in violations if v["severity"] == "ERROR"]) == 0,
            "violations": violations,
            "total_violations_count": violation_count
        }

    def generate_static_charts(self, df: pd.DataFrame, profile: dict, output_dir: str, specs: list = None) -> list:
        os.makedirs(output_dir, exist_ok=True)
        generated_paths = []
        
        classifications = profile.get("column_classifications") or self.classify_columns(df)
        if specs is None:
            specs = self.get_valid_charts_spec(df, classifications)
        
        plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
        
        for idx, spec in enumerate(specs):
            chart_type = spec["type"]
            x_col = spec["x_col"]
            y_col = spec["y_col"]
            title = spec["title"]
            
            plt.figure(figsize=(7, 4))
            
            if chart_type == "line" and x_col and y_col:
                # Chronological sort and aggregate
                df_temp = df.copy()
                df_temp[x_col] = pd.to_datetime(df_temp[x_col], errors='coerce')
                df_temp = df_temp.dropna(subset=[x_col]).sort_values(x_col)
                
                # Group by Date or Period
                df_grouped = df_temp.groupby(df_temp[x_col].dt.to_period('M'))[y_col].sum().reset_index()
                df_grouped[x_col] = df_grouped[x_col].astype(str)
                
                plt.plot(df_grouped[x_col], df_grouped[y_col], marker='o', color='#2563EB', linewidth=2)
                plt.title(title, fontsize=12, fontweight='bold', pad=10)
                plt.xlabel(x_col, fontsize=10)
                plt.ylabel(y_col, fontsize=10)
                plt.xticks(rotation=30, ha='right')
                
            elif chart_type == "bar" and x_col and y_col:
                df_grouped = df.groupby(x_col)[y_col].sum().sort_values(ascending=False).head(10)
                plt.bar(df_grouped.index, df_grouped.values, color='#1E293B', edgecolor='#2563EB', alpha=0.9)
                plt.title(title, fontsize=12, fontweight='bold', pad=10)
                plt.xlabel(x_col, fontsize=10)
                plt.ylabel(f"Total {y_col}", fontsize=10)
                plt.xticks(rotation=30, ha='right')
                
            elif (chart_type == "horizontalBar" or chart_type == "horizontal_bar") and x_col and y_col:
                df_grouped = df.groupby(x_col)[y_col].sum().sort_values(ascending=True).head(10)
                plt.barh(df_grouped.index, df_grouped.values, color='#1E293B', edgecolor='#2563EB', alpha=0.9)
                plt.title(title, fontsize=12, fontweight='bold', pad=10)
                plt.ylabel(x_col, fontsize=10)
                plt.xlabel(f"Total {y_col}", fontsize=10)
                
            elif chart_type == "pie" and x_col:
                df_counts = df[x_col].value_counts().head(6)
                plt.pie(df_counts.values, labels=df_counts.index, autopct='%1.1f%%', 
                        startangle=140, colors=['#2563EB', '#1E293B', '#10B981', '#F59E0B', '#EF4444', '#EC4899'])
                plt.title(title, fontsize=12, fontweight='bold', pad=10)
                
            elif chart_type == "scatter" and x_col and y_col:
                plt.scatter(df[x_col], df[y_col], color='#2563EB', alpha=0.6, edgecolors='none')
                plt.title(title, fontsize=12, fontweight='bold', pad=10)
                plt.xlabel(x_col, fontsize=10)
                plt.ylabel(y_col, fontsize=10)
                
            elif chart_type == "heatmap":
                numerics = [col for col, cls in classifications.items() if cls == "Numerical"]
                if len(numerics) >= 2:
                    corr = df[numerics].corr()
                    im = plt.imshow(corr, cmap='coolwarm', vmin=-1, vmax=1)
                    plt.colorbar(im)
                    plt.xticks(range(len(numerics)), numerics, rotation=45, ha='right')
                    plt.yticks(range(len(numerics)), numerics)
                    plt.title(title, fontsize=12, fontweight='bold', pad=10)
                    
            plt.tight_layout()
            if idx == 0:
                name = "trend_chart.png"
            elif idx == 1:
                name = "category_chart.png"
            elif idx == 2:
                name = "distribution_chart.png"
            else:
                name = f"chart_{spec['id']}.png"
                
            path = os.path.join(output_dir, name)
            plt.savefig(path, dpi=150)
            plt.close()
            generated_paths.append(path)
            
        return generated_paths
