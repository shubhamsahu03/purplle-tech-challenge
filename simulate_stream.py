import json
import time
import requests
import os

# Point this to wherever you saved the offline ML output
JSONL_PATH = "data_storage/artifacts/events.jsonl"
API_URL = "http://localhost:8000/events/ingest"
BATCH_SIZE = 50

def stream_events():
    print("🎥 Initiating Live CCTV Stream Simulation...")
    
    if not os.path.exists(JSONL_PATH):
        print(f"❌ Error: Could not find '{JSONL_PATH}'. Ensure your ML pipeline output is placed here.")
        return

    try:
        with open(JSONL_PATH, 'r') as f:
            events = [json.loads(line.strip()) for line in f if line.strip()]
    except Exception as e:
        print(f"❌ Error reading JSONL: {e}")
        return

    # Sort events chronologically to simulate a real passage of time
    events.sort(key=lambda x: x['timestamp'])
    
    batch = []
    total_pushed = 0
    
    print(f"📡 Found {len(events)} events. Streaming to {API_URL}...")
    
    for ev in events:
        batch.append(ev)
        
        if len(batch) >= BATCH_SIZE:
            try:
                response = requests.post(API_URL, json=batch)
                if response.status_code == 200:
                    total_pushed += len(batch)
                    print(f"✅ POSTed batch of {len(batch)} events (Total: {total_pushed}). Check the live dashboard!")
                else:
                    print(f"⚠️ API returned status {response.status_code}: {response.text}")
            except requests.exceptions.ConnectionError:
                print("❌ Connection Error: Is the FastAPI server running? (Run docker-compose up first)")
                return
            
            # 2-second delay to show the metrics updating "live" on the Streamlit dashboard
            time.sleep(2) 
            batch = []
            
    # Push any remaining events in the final batch
    if batch:
        try:
            response = requests.post(API_URL, json=batch)
            if response.status_code == 200:
                total_pushed += len(batch)
                print(f"✅ POSTed final batch of {len(batch)} events (Total: {total_pushed}).")
        except requests.exceptions.ConnectionError:
            print("❌ Connection Error on final batch.")

    print("🏁 CCTV Stream Complete.")

if __name__ == "__main__":
    stream_events()