# pip install fastapi uvicorn psutil matplotlib aiofiles sqlite3 aioredis websockets google-cloud-compute

from fastapi import FastAPI, BackgroundTasks, WebSocket
from fastapi.responses import StreamingResponse
import psutil
import asyncio
import threading
import time
import io
import sqlite3
import matplotlib.pyplot as plt
from datetime import datetime
import subprocess

from google.cloud import compute_v1

PROJECT_ID = "project-1-autoscale-gcp-vm" #Replace with your project ID
ZONE = "us-central1-a" #replace with your zone
MACHINE_TYPE = "e2-micro" #replace with your machine type
IMAGE_NAME = "debian-11-bullseye-v20240409" #replace with your image name or family

def create_gcp_instance():
    instance_client = compute_v1.InstancesClient()

    instance = compute_v1.Instance()
    instance.name = f"auto-scaled-instance-{datetime.now().strftime('%Y%m%d%H%M%S')}" #Unique name
    instance.machine_type = f"zones/{ZONE}/machineTypes/{MACHINE_TYPE}"

    disk = compute_v1.AttachedDisk()
    disk.initialize_params.source_image = f"projects/debian-cloud/global/images/debian-11" #using a public image
    disk.auto_delete = True
    disk.boot = True
    instance.disks = [disk]

    instance.network_interfaces = [compute_v1.NetworkInterface(name="global/networks/default")]

    try:
        operation = instance_client.insert(project=PROJECT_ID, zone=ZONE, instance_resource=instance)
        print(f"Launched GCP VM: {operation}")
        operation.result() # Wait for the operation to complete
        print(f"Instance {instance.name} created successfully.")
    except Exception as e:
        print(f"Error creating instance: {e}")



app = FastAPI()

cpu_ram_data = []
stress_ng_process = None
cpu_overload_start = None

# Initialize SQLite database
conn = sqlite3.connect("system_usage.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        cpu_usage REAL,
        ram_usage REAL
    )
''')
conn.commit()

async def update_usage():
    """Continuously updates CPU & RAM usage every 5 seconds and checks overload."""
    global cpu_overload_start

    while True:
        cpu_usage = psutil.cpu_percent(interval=1)
        ram_usage = psutil.virtual_memory().percent
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Store in database
        cursor.execute("INSERT INTO usage (timestamp, cpu_usage, ram_usage) VALUES (?, ?, ?)",
                       (timestamp, cpu_usage, ram_usage))
        conn.commit()

        # Store in memory (keep last 20 records)
        cpu_ram_data.append((timestamp, cpu_usage, ram_usage))
        if len(cpu_ram_data) > 20:
            cpu_ram_data.pop(0)

        # Check if CPU usage is above 75%
        if cpu_usage > 75:
            if cpu_overload_start is None:
                cpu_overload_start = time.time()
            elif time.time() - cpu_overload_start >= 10:  # If overload persists for 10 seconds
                if stress_ng_process is None or stress_ng_process.poll() is not None:
                    print("CPU overload detected! Increasing CPU load with stress-ng and creating instance...")
                    start_cpu_load()
                    create_gcp_instance()
        else:
            cpu_overload_start = None  # Reset overload timer

        await asyncio.sleep(5)

@app.get("/start_cpu_load") #changed to get
async def start_cpu_load():
    """Starts stress-ng process to increase CPU load."""
    global stress_ng_process
    if stress_ng_process is None or stress_ng_process.poll() is not None:
        try:
            stress_ng_process = subprocess.Popen(["stress-ng", "--cpu", str(psutil.cpu_count() // 2), "--timeout", "20s"]) # using half the cores for 20 seconds.
            create_gcp_instance()
            return {"message": "CPU load started."}
        except FileNotFoundError:
            return {"error": "stress-ng not found. Please install it."}
        except Exception as e:
            return {"error": f"Error starting stress-ng: {e}"}
    return {"message":"CPU load already running"}

@app.get("/stop_cpu_load") #changed to get
async def stop_cpu_load():
    """Stops the stress-ng process."""
    global stress_ng_process
    if stress_ng_process and stress_ng_process.poll() is None:
        stress_ng_process.terminate()
        stress_ng_process.wait()  # Wait for the process to terminate
        stress_ng_process = None
        return {"message": "CPU load stopped."}
    else:
        return {"message": "No stress-ng process to stop."}

@app.get("/startup")
async def startup_event():
    """Starts CPU & RAM monitoring when FastAPI launches."""
    asyncio.create_task(update_usage())

@app.get("/cpu_ram")
async def get_cpu_ram_usage():
    """Returns the latest CPU & RAM usage data."""
    cpu_usage = psutil.cpu_percent(interval=1)
    ram_usage = psutil.virtual_memory().percent
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cpu_usage": cpu_usage,
        "ram_usage": ram_usage
    }

@app.get("/cpu_ram_graph")
async def get_cpu_ram_graph():
    """Generates a live CPU & RAM usage graph and sends it as an image."""
    times, cpu_usages, ram_usages = zip(*cpu_ram_data) if cpu_ram_data else ([], [], [])

    plt.figure(figsize=(8, 4))
    plt.plot(times, cpu_usages, marker='o', linestyle='-', color='b', label="CPU Usage")
    plt.plot(times, ram_usages, marker='s', linestyle='-', color='r', label="RAM Usage")
    plt.xlabel('Time')
    plt.ylabel('Usage (%)')
    plt.title('Real-time CPU & RAM Usage')
    plt.legend()
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.tight_layout()

    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plt.close()

    return StreamingResponse(img, media_type="image/png")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for live updates."""
    await websocket.accept()
    try:
        while True:
            cpu_usage = psutil.cpu_percent(interval=1)
            ram_usage = psutil.virtual_memory().percent
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            await websocket.send_json({
                "timestamp": timestamp,
                "cpu_usage": cpu_usage,
                "ram_usage": ram_usage
            })
            await asyncio.sleep(5)
    except Exception as e:
        print("WebSocket error:", e)
    finally:
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="192.168.247.123", port=8000)

# Run the app in the VM
# python cpu_monitor.py

# Monitor CPU usage
# curl http://192.168.247.123:8000/cpu_ram

# Increase CPU load
# curl http://192.168.247.123:8000/start_cpu_load

# Reduce CPU load
# curl http://192.168.247.123:8000/stop_cpu_load

# CPU graph
# http://192.168.