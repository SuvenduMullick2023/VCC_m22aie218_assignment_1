#pip install fastapi uvicorn psutil matplotlib aiofiles sqlite3 aioredis websockets

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

app = FastAPI()

cpu_ram_data = []
cpu_load_threads = []
running = False

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
    """Continuously updates CPU & RAM usage every 5 seconds."""
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

        await asyncio.sleep(5)

def cpu_stress_task():
    """Consumes CPU cycles artificially."""
    while running:
        _ = [x**2 for x in range(10**6)]  # Heavy computation

@app.on_event("startup")
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

@app.get("/start_cpu_load")
async def start_cpu_load():
    """Starts a CPU-intensive process."""
    global running, cpu_load_threads
    if not running:
        running = True
        for _ in range(psutil.cpu_count() // 2):  # Use half the CPU cores
            thread = threading.Thread(target=cpu_stress_task)
            thread.start()
            cpu_load_threads.append(thread)
    return {"message": "CPU load increased"}

@app.get("/stop_cpu_load")
async def stop_cpu_load():
    """Stops the CPU-intensive process."""
    global running, cpu_load_threads
    running = False
    for thread in cpu_load_threads:
        thread.join()
    cpu_load_threads.clear()
    return {"message": "CPU load stopped"}

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
    uvicorn.run(app, host="192.168.148.123", port=8000)


#run the app in the VM    
#python cpu_monitor.py

#monitor cpu usage
#curl http://127.0.0.1:8000/cpu

#increase CPU load
#curl http://127.0.0.1:8000/start_cpu_load

#reduce CPU load
#curl http://127.0.0.1:8000/stop_cpu_load

#cpu graph
#http://127.0.0.1:8000/cpu_graph


   

		
		
    	
