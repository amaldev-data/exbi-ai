# Agentic Analytics OS (Portfolio Project Edition)

An asynchronous, multi-agent AI-powered data analytics consulting platform designed to simulate a real-world data science consulting team. 

This platform allows users to upload CSV/Excel files, automatically determines the dataset's business domain, recommends custom analyses, conducts a virtual department kickoff meeting, profiles, cleans and validates the data against business rules, builds interactive dashboards, and publishes download-ready PDF and Word reports.

---

## Key Features

1. **Dataset Discovery & Domain Autodetect**: The system profiles shape, data types, and null value densities, then uses LLM querying to infer the business domain (Sales, HR, Churn, or Operations).
2. **Requirements Recommendation**: Dynamically generates tailored analytical roadmaps matching the domain.
3. **14 Coordinating AI Agents**: Features specialized agents communicating over a shared state blackboard (using an SQLite persistent log database).
4. **Virtual Kickoff Meeting**: Simulates a detailed team chat where 9 department leaders argue priorities, align on validations, and finalize the Project Strategy.
5. **Deduplication & Imputation**: Executes Pandas pipelines to drop duplicate records and impute missing variables.
6. **Business Constraint Checking**: Identifies numeric violations (negative values in sales/incomes) and statistical outliers.
7. **Chart.js Dashboard**: Renders interactive, styled KPI cards, bar charts, trend lines, and pie charts.
8. **Automated Publishing**: Generates styled PDF reports (via ReportLab flowables) and Word documents (via python-docx) embedding backend Matplotlib charts.
9. **Zero API Cost & Dual-Mode Execution**: Operates using local Ollama instances (`llama3`, `mistral`, `gemma`, `qwen`) and falls back to a smart Analytical Template Engine if no LLM server is online (ideal for free-tier Render cloud hosting).
10. **Recruiter Sandbox Mode**: Recruiters can load pre-constructed sample datasets (Sales, HR) to test the entire application instantly without uploading files.

---

## Agent Network Design

The system runs 14 specialized agents coordinated by a **Program Manager Agent**:

| Department | Agent Persona | Responsibilities |
|---|---|---|
| **Discovery** | 1. Dataset Discovery Agent | Profiles schema, detects dates, and identifies business domain. |
| **Requirements** | 2. Requirement Recommendation Agent | Suggests specific analyses and dashboard targets. |
| **Business Analysis** | 3. Business Analyst Agent | Interprets requirements, creates the Business Requirement Document (BRD). |
| | 4. Analytics Strategy Agent | Translates the BRD into a technical project strategy and validations roadmap. |
| **Kickoff Meeting** | -- Meeting Facilitator | Convenes and records dialogue consensus between all department heads. |
| **Data Quality** | 5. Data Profiling Agent | Computes null densities, duplicates, and outlier records. |
| | 6. Data Cleaning Agent | Executes Pandas imputation (median and placeholder replacements). |
| | 7. Data Quality Validation Agent | Checks business rule logic (non-negatives constraints). |
| | 8. Data QA Agent | Reviews cleanup stats, issues the Data Quality Certification. |
| **Visualization** | 9. Visualization Planner Agent | Maps out layout blueprints (grid column formats, KPI selectors). |
| | 10. Visualization Builder Agent | Compiles Chart.js configurations and renders Matplotlib charts. |
| | 11. Visualization QA Agent | Verifies chart title labels and corporate brand color compliance. |
| **Reporting** | 12. Executive Report Writer | Authors structured executive markdown reports. |
| | 13. Report QA Agent | Audits report consistency, spelling, and professional tone. |
| **Governance** | 14. Executive QA Agent | Signs off the project with the Final Governance Certificate. |

---

## Folder Structure

```
agentic-analytics-os/
├── index.html             # Workspace setup, sample loaders, portfolio hub
├── dashboard.html         # Active results dashboard, logs terminal, widgets
├── reports.html           # Markdown previewer and document downloads
├── assets/
│   ├── css/
│   │   └── styles.css     # Consulting theme variables
│   └── js/
│       └── app.js         # State coordinator, AJAX calls, Chart.js builder
├── backend/
│   ├── main.py            # FastAPI main endpoints
│   ├── settings.json      # LLM host configs
│   ├── database/          # Persistent SQLite layer
│   │   ├── db_manager.py
│   │   └── analytics_platform.db
│   ├── services/          # Pandas, Matplotlib, ReportLab engines
│   │   ├── data_engine.py
│   │   ├── report_generator.py
│   │   └── llm_service.py
│   └── agents/            # Individual agent classes
│       ├── base.py
│       ├── discovery_agent.py
│       ├── recommendation_agent.py
│       ├── business_analyst.py
│       ├── strategist.py
│       ├── quality_agents.py
│       ├── viz_agents.py
│       ├── report_agents.py
│       └── executive_qa.py
├── requirements.txt       # Python package list
└── README.md              # Documentation
```

---

## Installation & Setup

### Prerequisites
* Python 3.10+
* (Optional) [Ollama](https://ollama.com/) running locally with the `llama3` model.

### 1. Run the Backend Server
1. Clone the repository and navigate to the project directory:
   ```bash
   cd agentic-analytics-os
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the FastAPI backend:
   ```bash
   uvicorn backend.main:app --reload
   ```
   *The server runs on `http://127.0.0.1:8000` by default.*

### 2. Run the Frontend
Because the frontend consists of pure, static HTML/CSS/JS files, you do not need node/npm servers!
* Simply open `index.html` in your web browser.
* *Recruiter Tip:* If hosting the static frontend on GitHub Pages, open the **Settings** modal in the sidebar and enter your hosted FastAPI backend Render URL (e.g., `https://your-backend.onrender.com`).

---

## Deployment Guide

### Frontend (GitHub Pages)
1. Commit the repository to a GitHub repository.
2. In the repository settings, go to **Pages**, select **Deploy from a branch**, and choose `/root` or the main branch.
3. Save and copy the public URL.

### Backend (Render Free Tier)
1. Create a new **Web Service** on Render, linking to your repository.
2. Select **Python** runtime environment.
3. Build Command:
   ```bash
   pip install -r requirements.txt
   ```
4. Start Command:
   ```bash
   uvicorn backend.main:app --host 0.0.0.0 --port $PORT
   ```
5. Add environment variable: `PYTHONUNBUFFERED=1`.
