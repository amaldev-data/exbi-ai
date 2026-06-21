import os
import sys

# Resolve absolute path to the parent directory to ensure 'backend' namespace works
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

import uuid
import json
import logging
import pandas as pd
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database.db_manager import init_db, get_db, Project, AgentLog
from backend.services.llm_service import LLMService
from backend.agents.orchestrator import ProgramManagerOrchestrator
from backend.config import TEMP_UPLOADS, TEMP_REPORTS, TEMP_CHARTS, TEMP_EXPORTS, TEMP_CACHE, ensure_temp_dirs
import asyncio
import time
import zipfile

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="exbi ai API", version="1.0.0")

# Enable CORS for static GitHub Pages frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for the static portfolio deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Configuration State
CONFIG_FILE = "backend/settings.json"
DEFAULT_SETTINGS = {
    "ollama_url": "http://localhost:11434",
    "model": "llama3"
}

def load_settings():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(settings, f, indent=2)

settings = load_settings()
llm_service = LLMService(ollama_url=settings["ollama_url"], model=settings["model"])

# Pydantic schemas
class SelectedRequirements(BaseModel):
    analyses: List[str]
    problem: str = ""
    decision: str = ""
    audience: str = ""
    objective: str = ""
    level: str = ""

class SettingsUpdate(BaseModel):
    ollama_url: str
    model: str

# Helper for background file deletion after a delay
async def delete_file_after_delay(path: str, delay: int = 60):
    await asyncio.sleep(delay)
    if os.path.exists(path):
        try:
            os.remove(path)
            logger.info(f"Automatically cleaned up file: {path} after {delay} seconds delay.")
        except Exception as e:
            logger.warning(f"Could not delete temporary file {path}: {e}")

# Inactivity-based cleanup engine running in background
def run_cleanup():
    now = time.time()
    max_age_seconds = 15 * 60  # 15 minutes of inactivity
    deleted_count = 0
    
    logger.info("Starting automated cleanup scan...")
    for folder in [TEMP_UPLOADS, TEMP_REPORTS, TEMP_CHARTS, TEMP_EXPORTS, TEMP_CACHE]:
        if not os.path.exists(folder):
            continue
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            # Skip directories
            if os.path.isdir(file_path):
                continue
            try:
                file_age = now - os.path.getmtime(file_path)
                if file_age > max_age_seconds:
                    os.remove(file_path)
                    logger.info(f"Cleanup: Deleted expired temporary file {file_path} (Age: {int(file_age/60)} mins)")
                    deleted_count += 1
            except Exception as e:
                logger.warning(f"Cleanup: Failed to delete {file_path}: {e}")
    logger.info(f"Automated cleanup finished. Deleted {deleted_count} files.")

async def cleanup_scheduler():
    while True:
        try:
            await asyncio.sleep(10 * 60)  # Sleep 10 minutes
            run_cleanup()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Cleanup scheduler encountered error: {e}")
            await asyncio.sleep(60)

# Startup Events: Init DB and Sample Datasets
@app.on_event("startup")
def startup_event():
    ensure_temp_dirs()
    init_db()
    asyncio.create_task(cleanup_scheduler())
    
    # Generate Sample Sales Dataset
    os.makedirs("backend/uploads", exist_ok=True)
    sales_path = "backend/uploads/sample_sales.csv"
    if not os.path.exists(sales_path):
        import numpy as np
        np.random.seed(42)
        dates = pd.date_range(start="2025-01-01", end="2025-04-30", freq="D")
        categories = ["Electronics", "Apparel", "Furniture", "Office Supplies", "Software"]
        regions = ["North America", "Europe", "Asia-Pacific", "Latin America"]
        
        data = {
            "Date": np.random.choice(dates, size=150),
            "Category": np.random.choice(categories, size=150, p=[0.3, 0.25, 0.15, 0.2, 0.1]),
            "Region": np.random.choice(regions, size=150),
            "Amount": np.round(np.random.uniform(50, 1200, size=150), 2),
            "Quantity": np.random.randint(1, 10, size=150)
        }
        
        # Add some missing values and negative values for cleaning testing
        df = pd.DataFrame(data)
        df.loc[5:10, "Amount"] = np.nan
        df.loc[12, "Amount"] = -250.00
        df.loc[25:27, "Category"] = None
        df.to_csv(sales_path, index=False)
        logger.info("Created sample sales dataset.")

    # Generate Sample HR Dataset
    hr_path = "backend/uploads/sample_hr.csv"
    if not os.path.exists(hr_path):
        import numpy as np
        np.random.seed(100)
        departments = ["Sales", "Research & Development", "Human Resources", "Engineering", "Marketing"]
        
        data = {
            "Employee_ID": [f"EMP{i:03d}" for i in range(1, 121)],
            "Age": np.random.randint(22, 60, size=120),
            "Department": np.random.choice(departments, size=120, p=[0.25, 0.35, 0.1, 0.2, 0.1]),
            "MonthlyIncome": np.random.randint(3000, 16000, size=120),
            "Attrition": np.random.choice(["Yes", "No"], size=120, p=[0.15, 0.85]),
            "Tenure": np.random.randint(1, 15, size=120)
        }
        df = pd.DataFrame(data)
        df.loc[10:13, "MonthlyIncome"] = np.nan
        df.loc[45, "Age"] = -5
        df.to_csv(hr_path, index=False)
        logger.info("Created sample HR dataset.")

@app.get("/")
def read_root():
    return {
        "status": "online",
        "project": "exbi ai API",
        "llm_provider_connected": llm_service.is_ollama_available(),
        "configured_model": llm_service.model
    }

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # Verify file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ['.csv', '.xlsx', '.xls']:
        raise HTTPException(status_code=400, detail="Unsupported file format. Upload CSV, XLSX, or XLS.")
        
    project_id = str(uuid.uuid4())[:8]
    file_path = os.path.join(TEMP_UPLOADS, f"raw_{project_id}{ext}")
    
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
        
    # Save project record
    project = Project(
        id=project_id,
        filename=file.filename,
        status="uploaded",
        file_path=file_path
    )
    db.add(project)
    db.commit()
    
    # Run Discovery Phase
    orchestrator = ProgramManagerOrchestrator(llm_service, db)
    try:
        state = orchestrator.run_discovery(project_id, file_path, file.filename)
        return {
            "project_id": project_id,
            "filename": file.filename,
            "dataset_info": state["dataset_info"],
            "recommendations": state["recommendations"]
        }
    except Exception as e:
        logger.error(f"Discovery phase failed: {e}")
        project.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Discovery phase failed: {str(e)}")

@app.post("/api/sample")
def load_sample(dataset_type: str = Form(...), db: Session = Depends(get_db)):
    if dataset_type == "sales":
        source_path = "backend/uploads/sample_sales.csv"
        filename = "sample_sales.csv"
    elif dataset_type == "hr":
        source_path = "backend/uploads/sample_hr.csv"
        filename = "sample_hr.csv"
    else:
        raise HTTPException(status_code=400, detail="Invalid sample dataset type.")
        
    project_id = str(uuid.uuid4())[:8]
    file_path = os.path.join(TEMP_UPLOADS, f"raw_{project_id}.csv")
    
    # Copy sample file to upload location
    import shutil
    shutil.copy(source_path, file_path)
    
    # Save project record
    project = Project(
        id=project_id,
        filename=filename,
        status="uploaded",
        file_path=file_path
    )
    db.add(project)
    db.commit()
    
    # Run Discovery Phase
    orchestrator = ProgramManagerOrchestrator(llm_service, db)
    try:
        state = orchestrator.run_discovery(project_id, file_path, filename)
        return {
            "project_id": project_id,
            "filename": filename,
            "dataset_info": state["dataset_info"],
            "recommendations": state["recommendations"]
        }
    except Exception as e:
        logger.error(f"Discovery phase failed: {e}")
        project.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Discovery phase failed: {str(e)}")

@app.post("/api/execute/{project_id}")
def execute_workflow(project_id: str, req: SelectedRequirements, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
        
    # Save selected analyses and user inputs to the database
    project.selected_analyses = json.dumps(req.analyses)
    
    # Store wizard choices in business_requirements under a user_inputs key
    user_inputs = {
        "problem": req.problem,
        "decision": req.decision,
        "audience": req.audience,
        "objective": req.objective,
        "level": req.level
    }
    project.business_requirements = json.dumps({"user_inputs": user_inputs})
    db.commit()
    
    # Queue Phase 2 workflow in background
    orchestrator = ProgramManagerOrchestrator(llm_service, db)
    background_tasks.add_task(orchestrator.run_full_workflow, project_id, req.analyses)
    
    return {"status": "queued", "project_id": project_id}

@app.get("/api/project/{project_id}")
def get_project_details(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
        
    # Load JSON fields safely
    def load_json(field):
        return json.loads(field) if field else None
        
    return {
        "id": project.id,
        "filename": project.filename,
        "status": project.status,
        "dataset_info": load_json(project.dataset_info),
        "selected_analyses": load_json(project.selected_analyses),
        "business_requirements": load_json(project.business_requirements),
        "analytics_strategy": load_json(project.analytics_strategy),
        "quality_report": load_json(project.quality_report),
        "dashboard_spec": load_json(project.dashboard_spec),
        "executive_report": project.executive_report,
        "approval_certificate": load_json(project.approval_certificate),
    }

@app.get("/api/project/{project_id}/logs")
def get_project_logs(project_id: str, db: Session = Depends(get_db)):
    logs = db.query(AgentLog).filter(AgentLog.project_id == project_id).order_by(AgentLog.timestamp.asc()).all()
    
    res = []
    for log in logs:
        res.append({
            "id": log.id,
            "timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "agent_name": log.agent_name,
            "target_agent": log.target_agent,
            "message": log.message,
            "log_type": log.log_type,
            "payload": json.loads(log.payload) if log.payload else None
        })
    return res

@app.get("/api/project/{project_id}/download/{file_type}")
def download_project_file(project_id: str, file_type: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
            
    if file_type == "cleaned_csv":
        file_path = os.path.join(TEMP_UPLOADS, f"cleaned_{project_id}.csv")
        media_type = "text/csv"
        filename = f"cleaned_{project.filename}"
    elif file_type == "cleaned_xlsx":
        file_path = os.path.join(TEMP_UPLOADS, f"cleaned_{project_id}.xlsx")
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"cleaned_{os.path.splitext(project.filename)[0]}.xlsx"
    elif file_type == "pdf":
        file_path = os.path.join(TEMP_REPORTS, f"executive_report_{project_id}.pdf")
        media_type = "application/pdf"
        filename = f"executive_report_{project_id}.pdf"
    elif file_type == "docx":
        file_path = os.path.join(TEMP_REPORTS, f"executive_report_{project_id}.docx")
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = f"executive_report_{project_id}.docx"
    elif file_type == "pptx":
        file_path = os.path.join(TEMP_REPORTS, f"executive_report_{project_id}.pptx")
        media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        filename = f"executive_report_{project_id}.pptx"
    elif file_type == "excel":
        file_path = os.path.join(TEMP_REPORTS, f"executive_report_{project_id}.xlsx")
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"executive_report_{project_id}.xlsx"
    elif file_type == "zip":
        zip_path = os.path.join(TEMP_REPORTS, f"project_results_{project_id}.zip")
        pdf_path = os.path.join(TEMP_REPORTS, f"executive_report_{project_id}.pdf")
        pptx_path = os.path.join(TEMP_REPORTS, f"executive_report_{project_id}.pptx")
        docx_path = os.path.join(TEMP_REPORTS, f"executive_report_{project_id}.docx")
        xlsx_report_path = os.path.join(TEMP_REPORTS, f"executive_report_{project_id}.xlsx")
        cleaned_csv = os.path.join(TEMP_UPLOADS, f"cleaned_{project_id}.csv")
        cleaned_xlsx = os.path.join(TEMP_UPLOADS, f"cleaned_{project_id}.xlsx")
        
        # Package whatever files exist
        files_to_zip = []
        for p, name in [
            (pdf_path, f"executive_report_{project_id}.pdf"),
            (pptx_path, f"executive_report_{project_id}.pptx"),
            (docx_path, f"executive_report_{project_id}.docx"),
            (xlsx_report_path, f"executive_report_{project_id}.xlsx"),
            (cleaned_xlsx, f"cleaned_{os.path.splitext(project.filename)[0]}.xlsx"),
            (cleaned_csv, f"cleaned_{os.path.splitext(project.filename)[0]}.csv"),
        ]:
            if os.path.exists(p):
                files_to_zip.append((p, name))
                
        if not files_to_zip:
            raise HTTPException(status_code=404, detail="No generated reports or datasets found to package.")
            
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for p, name in files_to_zip:
                zipf.write(p, arcname=name)
                
        media_type = "application/zip"
        filename = f"exbi_ai_results_{project_id}.zip"
        file_path = zip_path
        
        # Queue deletion for all files in the ZIP, the raw uploaded file, and the ZIP itself
        background_tasks.add_task(delete_file_after_delay, zip_path, delay=60)
        for p, _ in files_to_zip:
            background_tasks.add_task(delete_file_after_delay, p, delay=60)
        if project.file_path and os.path.exists(project.file_path):
            background_tasks.add_task(delete_file_after_delay, project.file_path, delay=60)
            
        return FileResponse(path=file_path, filename=filename, media_type=media_type)
    else:
        raise HTTPException(status_code=400, detail="Invalid download file type requested.")
        
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File {file_type} has not been generated yet or fails to exist.")
        
    # Queue auto-cleanup for the downloaded file (60 seconds)
    background_tasks.add_task(delete_file_after_delay, file_path, delay=60)
    
    return FileResponse(path=file_path, filename=filename, media_type=media_type)

class SessionClearRequest(BaseModel):
    project_id: str

@app.post("/api/session/clear")
def clear_session(req: SessionClearRequest, db: Session = Depends(get_db)):
    from backend.agents.session_manager import SessionManagerAgent
    mgr = SessionManagerAgent(llm_service, db)
    mgr.purge_session(req.project_id)
    return {"status": "cleared", "project_id": req.project_id}

@app.get("/api/settings")
def get_system_settings():
    return {
        "ollama_url": settings["ollama_url"],
        "model": settings["model"],
        "connected": llm_service.is_ollama_available()
    }

@app.post("/api/settings")
def update_system_settings(cfg: SettingsUpdate):
    settings["ollama_url"] = cfg.ollama_url
    settings["model"] = cfg.model
    save_settings(settings)
    
    # Re-instantiate LLM service
    global llm_service
    llm_service = LLMService(ollama_url=cfg.ollama_url, model=cfg.model)
    
    return {
        "status": "updated",
        "connected": llm_service.is_ollama_available()
    }
