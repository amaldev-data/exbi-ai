import os
import sys
import json
import shutil
import logging

# Ensure project root is in python path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.database.db_manager import init_db, SessionLocal, Project, AgentLog
from backend.services.llm_service import LLMService
from backend.agents.orchestrator import ProgramManagerOrchestrator
from backend.config import TEMP_UPLOADS, TEMP_REPORTS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VerifyRedesign")

def run_test_for_dataset(dataset_type: str, file_path: str, filename: str):
    logger.info(f"\n==================================================")
    logger.info(f"TESTING DATASET: {dataset_type.upper()} ({filename})")
    logger.info(f"==================================================")
    
    # 1. Initialize DB Session
    db = SessionLocal()
    project_id = f"test_{dataset_type}"
    
    # Clean up previous test project if exists
    existing = db.query(Project).filter(Project.id == project_id).first()
    if existing:
        db.delete(existing)
        db.commit()
    db.query(AgentLog).filter(AgentLog.project_id == project_id).delete()
    db.commit()
    
    # Copy file to mock upload path
    os.makedirs(TEMP_UPLOADS, exist_ok=True)
    raw_path = os.path.join(TEMP_UPLOADS, f"raw_{project_id}.csv")
    shutil.copy(file_path, raw_path)
    
    # Save project record
    project = Project(
        id=project_id,
        filename=filename,
        status="uploaded",
        file_path=raw_path
    )
    db.add(project)
    db.commit()
    
    # Mock LLM Service (can fall back or call Ollama if online)
    llm_service = LLMService(ollama_url="http://localhost:11434", model="llama3")
    orchestrator = ProgramManagerOrchestrator(llm_service, db)
    
    # 2. Run Phase 1 Ingestion & Discovery
    logger.info("Executing Phase 1 Ingestion & Discovery...")
    discovery_state = orchestrator.run_discovery(project_id, raw_path, filename)
    
    # Assertions on discovery
    assert "dataset_info" in discovery_state, "Discovery state missing 'dataset_info'"
    assert "recommendations" in discovery_state, "Discovery state missing 'recommendations'"
    
    dataset_info = discovery_state["dataset_info"]
    domain = dataset_info["business_discovery"]["business_domain"]
    cols = dataset_info["technical_profile"]["column_names"]
    classifications = dataset_info["technical_profile"]["column_classifications"]
    
    logger.info(f"Detected Business Domain: {domain}")
    logger.info(f"Dataset Columns: {cols}")
    logger.info(f"Column Classifications: {json.dumps(classifications, indent=2)}")
    
    assert len(cols) > 0, "No columns detected"
    assert len(classifications) == len(cols), "Not all columns classified"
    
    # Verify recommendations exist
    recs = discovery_state["recommendations"]
    logger.info(f"Generated Recommended Analyses: {[r['title'] for r in recs]}")
    assert len(recs) > 0, "No recommendations generated"
    
    # 3. Run Phase 2 Pipeline Execution
    logger.info("Executing Phase 2 Full Analytics Pipeline...")
    selected_analyses = [r["id"] for r in recs if r["recommended"]]
    if not selected_analyses:
        selected_analyses = [recs[0]["id"]]
        
    orchestrator.run_full_workflow(project_id, selected_analyses)
    
    # Reload project
    db.expire_all()
    project = db.query(Project).filter(Project.id == project_id).first()
    
    assert project.status == "completed", f"Workflow execution failed, project status is: {project.status}"
    
    # Assert deliverables exist and are populated
    dashboard_spec = json.loads(project.dashboard_spec)
    executive_report = project.executive_report
    quality_report = json.loads(project.quality_report)
    approval_cert = json.loads(project.approval_certificate)
    
    logger.info(f"Data Quality Score: {quality_report.get('quality_score')}/100")
    logger.info(f"KPIs Generated: {len(dashboard_spec['kpis'])}")
    for kpi in dashboard_spec["kpis"]:
        logger.info(f" - {kpi['title']}: {kpi['value']} ({kpi['description']})")
        
    logger.info(f"Charts Generated: {len(dashboard_spec['charts'])}")
    for chart in dashboard_spec["charts"]:
        logger.info(f" - [{chart['type'].upper()}] {chart['title']}: {chart['description']}")
        
    assert len(dashboard_spec["kpis"]) >= 3, "Insufficient KPIs generated"
    assert len(dashboard_spec["charts"]) > 0, "No charts generated"
    assert len(executive_report) > 0, "Executive report is empty"
    assert approval_cert["status"] == "APPROVED", "Project was not certified and approved"
    
    # Verify outputs directory for generated assets
    reports_dir = TEMP_REPORTS
    pdf_path = os.path.join(reports_dir, f"executive_report_{project_id}.pdf")
    docx_path = os.path.join(reports_dir, f"executive_report_{project_id}.docx")
    pptx_path = os.path.join(reports_dir, f"executive_report_{project_id}.pptx")
    xlsx_path = os.path.join(reports_dir, f"executive_report_{project_id}.xlsx")
    
    assert os.path.exists(pdf_path), "PDF report missing"
    assert os.path.exists(docx_path), "Word report missing"
    assert os.path.exists(pptx_path), "Presentation slides missing"
    assert os.path.exists(xlsx_path), "Excel report missing"
    
    logger.info("Deliverable file checks passed!")
    logger.info("PDF: " + pdf_path)
    logger.info("DOCX: " + docx_path)
    logger.info("PPTX: " + pptx_path)
    logger.info("XLSX: " + xlsx_path)
    
    db.close()
    logger.info(f"SUCCESS: E2E Pipeline verified for dataset: {dataset_type}")

def main():
    try:
        from backend.main import startup_event
        startup_event()
        logger.info("Database and sample datasets successfully initialized.")
    except Exception as e:
        logger.warning(f"Could not run startup_event: {e}")
        init_db()
    
    # Test Sales Dataset
    sales_path = "backend/uploads/sample_sales.csv"
    if os.path.exists(sales_path):
        run_test_for_dataset("sales", sales_path, "sample_sales.csv")
    else:
        logger.error(f"Sample sales file not found at {sales_path}.")
        
    # Test HR Dataset
    hr_path = "backend/uploads/sample_hr.csv"
    if os.path.exists(hr_path):
        run_test_for_dataset("hr", hr_path, "sample_hr.csv")
    else:
        logger.error(f"Sample HR file not found at {hr_path}.")

if __name__ == "__main__":
    main()
