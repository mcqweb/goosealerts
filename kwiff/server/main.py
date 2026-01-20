from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create data folder if it doesn't exist
DATA_FOLDER = "data"
Path(DATA_FOLDER).mkdir(exist_ok=True)


@app.post("/submit")
async def submit_json(request: Request):
    """
    Accept JSON submission, store it in data folder, and return the same JSON.
    
    Handles three types of submissions:
    1. Single event data: stored as {eventId}_kwiff.json
    2. Multiple events: stored as events_YYYYMMDD.json (overwrites daily)
    3. Combo odds data: stored as combos_YYYYMMDD.json (overwrites daily)
    
    Returns the submitted JSON
    """
    try:
        # Read the JSON body
        body = await request.json()
        
        # Determine file type and extract event ID
        if 'events' in body and isinstance(body['events'], list) and len(body['events']) > 0:
            # Check if events contain combos (multi-event combo submission)
            has_combos = any(event.get('combos') for event in body['events'])
            
            if has_combos:
                # Combo odds submission - use today's date as filename
                today = datetime.now().strftime("%Y%m%d")
                filename = f"combos_{today}.json"
            elif len(body['events']) == 1:
                # Single event - use event-based filename
                event_id = body['events'][0].get('eventId')
                if not event_id:
                    return JSONResponse(
                        status_code=400,
                        content={"error": "Event submission missing eventId"}
                    )
                filename = f"{event_id}_kwiff.json"
            else:
                # Multiple events without combos - use today's date as filename
                today = datetime.now().strftime("%Y%m%d")
                filename = f"events_{today}.json"
        elif 'combos' in body:
            # Top-level combo odds submission (legacy format) - use today's date as filename
            today = datetime.now().strftime("%Y%m%d")
            filename = f"combos_{today}.json"
        else:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid JSON: must contain 'events' or 'combos' key"}
            )
        
        # Store the JSON to file (replaces existing file with same name)
        filepath = os.path.join(DATA_FOLDER, filename)
        with open(filepath, 'w') as f:
            json.dump(body, f, indent=2)
        
        # Debug: Save a copy with timestamp
        debug_dir = os.path.join(DATA_FOLDER, "debug")
        Path(debug_dir).mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_filepath = os.path.join(debug_dir, f"{timestamp}_submitted_{filename}")
        with open(debug_filepath, 'w') as f:
            json.dump(body, f, indent=2)
        
        # Return the same JSON with metadata about the save
        response = {
            "data": body,
            "saved": True,
            "filename": filename,
            "filepath": filepath,
            "timestamp": datetime.now().isoformat()
        }
        return response
    
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid JSON"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get("/")
def read_root():
    return {"message": "FastAPI JSON Storage Server", "endpoint": "/submit (POST)"}


@app.get("/combos")
def get_combos(min_size: float = 10.0):
    """
    Generate combo JSON for all events in today's batch file.
    
    Parameters:
    - min_size: Minimum lay size in GBP (default: 10.0)
    
    Returns:
    - JSON with all matched player combos grouped by event
    """
    try:
        # Get the directory of this file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        generate_script = os.path.join(script_dir, "generate_combos.py")
        
        # Get the Python executable from the venv
        if sys.platform == "win32":
            python_exe = os.path.join(script_dir, ".venv", "Scripts", "python.exe")
        else:
            python_exe = os.path.join(script_dir, ".venv", "bin", "python")
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Running combo generation: min_size={min_size}")
        
        # Run the generate_combos script with longer timeout (300 seconds = 5 minutes for API calls)
        result = subprocess.run(
            [python_exe, generate_script, "--min-size", str(min_size)],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] Script error: {result.stderr}")
            return JSONResponse(
                status_code=500,
                content={"error": f"Script error: {result.stderr}"}
            )
        
        # Parse and return the JSON output
        combo_data = json.loads(result.stdout)
        total_combos = sum(len(event.get('combos', [])) for event in combo_data.get('events', []))
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Successfully generated {total_combos} combos across {len(combo_data.get('events', []))} events")
        
        # Debug: Save the response
        debug_dir = os.path.join(script_dir, DATA_FOLDER, "debug")
        Path(debug_dir).mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_filepath = os.path.join(debug_dir, f"{timestamp}_combos_response.json")
        with open(debug_filepath, 'w') as f:
            json.dump(combo_data, f, indent=2)
        
        return combo_data
        
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Invalid JSON from script: {str(e)}"}
        )
    except subprocess.TimeoutExpired:
        print(f"Script timeout after 300 seconds")
        return JSONResponse(
            status_code=504,
            content={"error": "Script execution timeout - Betfair API calls may be slow"}
        )
    except Exception as e:
        print(f"Unexpected error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error generating combos: {str(e)}"}
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
