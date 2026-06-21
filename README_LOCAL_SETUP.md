# Agentic Analytics OS - Local Setup Guide

This guide provides simple, step-by-step instructions to run **Agentic Analytics OS** on your Windows laptop.

---

## Prerequisites
* **Windows 10 or 11**
* **Python 3.10 or higher** (Make sure to check **"Add Python to PATH"** during installation)
* (Optional) **Ollama** installed locally if you want to use actual local LLMs (defaults to `llama3` on `http://localhost:11434`). If Ollama is not active, the system automatically uses the built-in data-aware fallbacks.

---

## Quick Start (Two Batch Scripts)

We have provided two automated batch scripts so you do not have to write manual console commands:

### 1. First-time Setup (`setup.bat`)
* Double-click the **`setup.bat`** file in the root folder.
* This script will automatically:
  1. Detect your Python version.
  2. Create a virtual environment (`venv`).
  3. Activate the environment.
  4. Upgrade pip and install all required libraries (`FastAPI`, `Pandas`, `Matplotlib`, `ReportLab`, `python-docx`, `SQLAlchemy`, etc.).
  5. Chain-launch the application once completed.

### 2. One-click Launcher (`run.bat`)
* For subsequent launches, double-click **`run.bat`**.
* This script will automatically:
  1. Verify the virtual environment is present.
  2. Create missing upload and report directories if needed (`backend/uploads`, `backend/reports`).
  3. Start the FastAPI backend server in a separate, dedicated command prompt window (so you can view runtime agent logs).
  4. Open your default web browser to **`http://localhost:3000`**.
  5. Start a local HTTP server for the frontend workspace in the current window.

---

## Workspace Features & How to Test

Once the web page opens:
1. **Upload Zone**: Drag and drop any Excel (`.xlsx`, `.xls`) or CSV file, or click to browse.
2. **Sandbox Mode (Recommended)**: If you don't have a dataset ready, click **"Load Sample Sales Data"** or **"Load Sample HR Data"** in the sidebar. This loads a realistic mock dataset containing missing values, duplicates, and business anomalies directly into the memory.
3. **Analyses Checklist**: Check the analytical modules you want to execute (e.g. Sales growth, forecasting, PDF report creation).
4. **Agent Monitor Panel**: Once you click **"Execute"**, you will be redirected to the dashboard. You can watch:
   * A progress timeline.
   * A scrolling terminal log showing conversation exchanges (like the kickoff meeting dialogue) between the 15 agents.
   * Pulsing indicators indicating which agent node is currently running in the background.
5. **Download Center**: Once the workflow finishes, download the cleaned CSV, cleaned Excel, executive PDF report (with embedded charts), and Word DOCX report from the downloads section.

---

## Troubleshooting Guide

### "Python not recognized"
* **Cause**: Python was installed but the installer option "Add Python to PATH" was not checked.
* **Fix**: Re-run the Python installer, select **Modify**, check **Add Python to PATH**, and click through the installer steps. Restart your terminal or command prompt.

### Port Conflicts (Port 8000 or Port 3000 already in use)
* **Cause**: Another service is running on local ports 8000 or 3000.
* **Fix**: If you need to customize ports:
  * Open `run.py` and change `port=8000` to a free port (e.g., `8080`).
  * Open `run.bat` and change `python -m http.server 3000` to another port (e.g., `http.server 3030`).
  * In the frontend page, click **Settings** in the bottom-left sidebar and update the FastAPI Backend URL to match the new port (e.g., `http://127.0.0.1:8080`).
