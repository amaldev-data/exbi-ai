import uvicorn
import os

if __name__ == "__main__":
    print("==========================================================")
    print("                    Launching exbi ai Backend             ")
    print("==========================================================")
    print("1. Backend API will run on http://127.0.0.1:8000")
    print("2. Open index.html in a web browser to run the UI.")
    print("3. SQLite database & sample files will initialize automatically.")
    print("==========================================================")
    
    # Run server
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
