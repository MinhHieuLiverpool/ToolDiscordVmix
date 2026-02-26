from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
from datetime import datetime, timedelta
import pytz
from pymongo import MongoClient, DESCENDING
import os
import sys
from typing import List

# Try to import from config.py
try:
    from config import MONGODB_URI, DATABASE_NAME, COLLECTION_NAME
    # Try to import DISCORD_WEBHOOK separately (optional)
    try:
        from config import DISCORD_WEBHOOK
    except ImportError:
        DISCORD_WEBHOOK = ''
except ImportError:
    MONGODB_URI = os.getenv('MONGODB_URI', '')
    DATABASE_NAME = os.getenv('DATABASE_NAME', 'vmix_monitor')
    COLLECTION_NAME = os.getenv('COLLECTION_NAME', 'logs')
    DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK', '')  # Optional Discord webhook

# Port configuration
PORT = int(os.getenv('PORT', 8088))

# Timezone configuration - Vietnam
VIETNAM_TZ = pytz.timezone('Asia/Ho_Chi_Minh')

# MongoDB connection
try:
    client = MongoClient(
        MONGODB_URI, 
        serverSelectionTimeoutMS=10000,
        tls=True,
        tlsAllowInvalidCertificates=True
    )
    db = client[DATABASE_NAME]
    collection = db[COLLECTION_NAME]
    selected_collection = db['selected_list']  # Collection mới cho selected list
    client.admin.command('ping')
    print("✓ Connected to MongoDB successfully!")
except Exception as e:
    print(f"✗ MongoDB connection error: {e}")
    sys.exit(1)

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active WebSocket connections
active_connections: List[WebSocket] = []
_last_broadcast: datetime = datetime.min.replace(tzinfo=pytz.UTC)
_broadcast_interval_sec = 1.0  # Broadcast tối đa 1 lần/giây

# ── In-memory cache ─────────────────────────────────────────────────────────────────
# Key: machine_name, Value: document dict
_data_cache: dict = {}

def send_discord_notification(machine_name: str, ipwan: str, port: str, status: str):
    """Gửi notification lên Discord (nếu có webhook)"""
    if not DISCORD_WEBHOOK:
        return
    
    try:
        import requests
        
        # Gửi text đơn giản thay vì embed
        message = f"[{machine_name}] SRT {status} | IPWAN: {ipwan} | PORT: {port}"
        payload = {"content": message}
        
        response = requests.post(DISCORD_WEBHOOK, json=payload, timeout=5)
        if response.status_code in [200, 204]:
            print(f"✓ Discord notification sent for {machine_name}")
        else:
            print(f"⚠ Discord webhook failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Discord notification error: {e}")

def get_all_logs():
    """Get all logs – served from in-memory cache (no MongoDB query)"""
    entries = []
    for doc in _data_cache.values():
        entry = {
            "timestamp": doc.get("last_updated", ""),
            "data": {
                "name":      doc.get("name", ""),
                "ip":        doc.get("ip", ""),
                "ipwan":     doc.get("ipwan", ""),
                "status":    doc.get("status", ""),
                "port":      doc.get("port", ""),
                "statusapp": doc.get("statusapp", 0),
                "ping":      doc.get("ping"),
                "ping_timeouts": doc.get("ping_timeouts", 0),
                "cpu":       doc.get("temperature"),
                "memory":    doc.get("memory"),
            }
        }
        entries.append(entry)
    return entries

@app.api_route("/", methods=["GET", "HEAD"])
async def health_check():
    """Health check endpoint for UptimeRobot - hỗ trợ cả GET và HEAD"""
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("I am alive!")

@app.get("/logs")
async def get_all_data():
    """GET endpoint - lấy tất cả dữ liệu"""
    return JSONResponse(content=get_all_logs())

@app.post("/")
async def receive_data(data: dict):
    """Nhận dữ liệu từ vMix"""
    try:
        timestamp = datetime.now(VIETNAM_TZ).isoformat()
        machine_name = data.get('name', data.get('ip', 'Unknown'))

        # ── 1. Cập nhật cache ngay lập tức (< 1ms, không block) ──
        prev = _data_cache.get(machine_name, {})
        document = {
            "name":        machine_name,
            "ip":          data.get('ip', ''),
            "ipwan":       data.get('ipwan', ''),
            "status":      data.get('status', 'UNKNOWN'),
            "port":        data.get('port', ''),
            "statusapp":   data.get('statusapp', 0),
            "ping":        data.get('ping'),
            "ping_timeouts": data.get('ping_timeouts', 0),
            "temperature": data.get('temperature'),
            "memory":      data.get('memory'),
            "last_updated": timestamp,
            "timestamp":   timestamp,
        }
        _data_cache[machine_name] = document

        # So sánh thay đổi với cache cũ (không cần query MongoDB)
        fields_to_check = ['ip', 'ipwan', 'status', 'port']
        has_changes = not prev or any(
            prev.get(f) != document.get(f) for f in fields_to_check
        )
        if has_changes and prev:
            for f in fields_to_check:
                if prev.get(f) != document.get(f):
                    print(f"  ⚠ {machine_name} {f}: {prev.get(f)} → {document.get(f)}")

        # ── 2. Broadcast từ cache (non-blocking) ──
        await broadcast_updates()

        # ── 3. Ghi MongoDB trong background (không đợi) ──
        asyncio.create_task(_mongo_upsert(machine_name, document))

        return JSONResponse(content={
            "status": "success",
            "message": f"Data received for {machine_name}",
            "changes_detected": has_changes,
        })

    except Exception as e:
        print(f"✗ Error processing data: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


async def _mongo_upsert(name: str, document: dict):
    """Ghi MongoDB bất đồng bộ – chạy trong thread pool, không block event loop"""
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(
            None,
            lambda: collection.update_one(
                {"name": name},
                {"$set": document},
                upsert=True
            )
        )
    except Exception as e:
        print(f"✗ MongoDB upsert error ({name}): {e}")

@app.post("/delete")
async def delete_data(payload: dict):
    """Xóa dữ liệu theo IP và Port"""
    try:
        name = payload.get('name', '')
        ip = payload.get('ip', '')
        port = payload.get('port', 0)
        
        # Xóa theo IP và Port để đảm bảo chính xác
        query = {
            "ip": ip,
            "port": port
        }
        
        result = collection.delete_one(query)
        
        if result.deleted_count > 0:
            print(f"✓ Deleted: {name} - {ip}:{port}")
            # Broadcast update to all WebSocket clients
            await broadcast_updates()
            return JSONResponse(content={
                "success": True, 
                "deleted": result.deleted_count,
                "message": f"Deleted {name} - {ip}:{port}"
            })
        else:
            print(f"⚠ Not found: {name} - {ip}:{port}")
            return JSONResponse(content={
                "success": False,
                "deleted": 0,
                "message": f"Not found: {name} - {ip}:{port}"
            })
    except Exception as e:
        print(f"✗ Delete error: {e}")
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)

@app.get("/get_by_ip")
async def get_by_ip(ip: str):
    """Lấy dữ liệu theo IP"""
    try:
        documents = collection.find({"ip": ip})
        entries = []
        
        for doc in documents:
            entry = {
                "timestamp": doc.get("last_updated", doc.get("timestamp", "")),
                "data": {
                    "name": doc.get("name", ""),
                    "ip": doc.get("ip", ""),
                    "ipwan": doc.get("ipwan", ""),
                    "status": doc.get("status", ""),
                    "port": doc.get("port", ""),
                    "statusapp": doc.get("statusapp", 0)
                }
            }
            entries.append(entry)
        
        return JSONResponse(content=entries)
    except Exception as e:
        print(f"✗ Get by IP error: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/update_name")
async def update_name(payload: dict):
    """Update name in MongoDB"""
    try:
        old_name = payload.get('old_name', '')
        new_name = payload.get('new_name', '')
        ip = payload.get('ip', '')
        
        result = collection.update_many(
            {"data.ip": ip},
            {"$set": {"data.name": new_name}}
        )
        
        print(f"✓ Updated {result.modified_count} documents: {old_name} → {new_name}")
        
        # Broadcast update to all WebSocket clients
        await broadcast_updates()
        
        return JSONResponse(content={"success": True, "modified": result.modified_count})
    except Exception as e:
        print(f"✗ Update error: {e}")
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)

@app.post("/update_ip")
async def update_ip(payload: dict):
    """Update IP in MongoDB when machine IP changes"""
    try:
        old_ip = payload.get('old_ip', '')
        new_ip = payload.get('new_ip', '')
        port = payload.get('port', 0)
        name = payload.get('name', '')
        
        # Update document với old_ip và port
        result = collection.update_one(
            {"ip": old_ip, "port": port},
            {"$set": {"ip": new_ip}}
        )
        
        if result.modified_count > 0:
            print(f"✓ Updated IP for {name} (Port {port}): {old_ip} → {new_ip}")
        else:
            print(f"⚠ No document found to update: {name} - {old_ip}:{port}")
        
        # Broadcast update to all WebSocket clients
        await broadcast_updates()
        
        return JSONResponse(content={
            "success": True, 
            "modified": result.modified_count,
            "message": f"Updated {name} IP: {old_ip} → {new_ip}"
        })
    except Exception as e:
        print(f"✗ Update IP error: {e}")
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)

@app.post("/save_selected_list")
async def save_selected_list(payload: dict):
    """Lưu selected list vào database"""
    try:
        selected_data = payload.get('selected_data', [])
        
        # Xóa toàn bộ selected list cũ và lưu mới
        selected_collection.delete_many({})
        
        if selected_data:
            selected_collection.insert_many(selected_data)
            print(f"✓ Saved {len(selected_data)} items to selected list")
        else:
            print("✓ Cleared selected list")
        
        return JSONResponse(content={
            "success": True, 
            "count": len(selected_data),
            "message": f"Saved {len(selected_data)} items"
        })
    except Exception as e:
        print(f"✗ Save selected list error: {e}")
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)

@app.get("/load_selected_list")
async def load_selected_list():
    """Load selected list từ database"""
    try:
        documents = selected_collection.find()
        entries = []
        
        for doc in documents:
            # Remove _id field from MongoDB
            doc.pop('_id', None)
            entries.append(doc)
        
        print(f"✓ Loaded {len(entries)} items from selected list")
        return JSONResponse(content=entries)
    except Exception as e:
        print(f"✗ Load selected list error: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for realtime updates"""
    await websocket.accept()
    active_connections.append(websocket)
    print(f"✓ WebSocket client connected. Total connections: {len(active_connections)}")
    
    try:
        # Send initial data
        data = get_all_logs()
        await websocket.send_json(data)
        
        # Keep connection alive and send updates every 5 seconds
        while True:
            data = get_all_logs()
            await websocket.send_json(data)
            await asyncio.sleep(5)
            
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        print(f"⚠ WebSocket client disconnected. Total connections: {len(active_connections)}")
    except Exception as e:
        print(f"✗ WebSocket error: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)

async def broadcast_updates():
    """Broadcast updates từ cache – throttled to once per second, không query MongoDB"""
    global _last_broadcast
    if not active_connections:
        return

    now = datetime.now(pytz.UTC)
    if (now - _last_broadcast).total_seconds() < _broadcast_interval_sec:
        return

    _last_broadcast = now
    data = get_all_logs()  # đọc từ cache, không có I/O
    disconnected = []
    
    for connection in active_connections:
        try:
            await connection.send_json(data)
        except Exception as e:
            print(f"✗ Failed to send to client: {e}")
            disconnected.append(connection)
    
    # Remove disconnected clients
    for connection in disconnected:
        active_connections.remove(connection)

async def check_inactive_machines():
    """Background task: tự động set statusapp=0 nếu máy không gửi request trong 1 phút"""
    while True:
        try:
            await asyncio.sleep(30)
            now = datetime.now(VIETNAM_TZ)
            timeout_threshold = now - timedelta(minutes=1)
            updated_count = 0

            for name, doc in list(_data_cache.items()):
                if doc.get("statusapp", 0) != 1:
                    continue
                last_str = doc.get("last_updated", "")
                if not last_str:
                    continue
                try:
                    last_updated = datetime.fromisoformat(last_str)
                    if last_updated < timeout_threshold:
                        _data_cache[name]["statusapp"] = 0
                        updated_count += 1
                        print(f"⏱️  Auto-OFF: {name} - No activity for 1 minute")
                        asyncio.create_task(_mongo_upsert(name, _data_cache[name]))
                except Exception as e:
                    print(f"⚠ Timestamp parse error {name}: {e}")

            if updated_count > 0:
                print(f"✓ Auto-OFF applied to {updated_count} machine(s)")
                await broadcast_updates()
        except Exception as e:
            print(f"✗ Error in check_inactive_machines: {e}")

@app.on_event("startup")
async def startup_event():
    """Preload cache từ MongoDB, khởi động background tasks"""
    loop = asyncio.get_event_loop()
    try:
        docs = await loop.run_in_executor(
            None,
            lambda: list(collection.find().sort("last_updated", DESCENDING).limit(500))
        )
        for doc in docs:
            name = doc.get("name")
            if name:
                _data_cache[name] = doc
        print(f"✓ Cache preloaded: {len(_data_cache)} machines from MongoDB")
    except Exception as e:
        print(f"✗ Cache preload error: {e}")
    asyncio.create_task(check_inactive_machines())
    print("✓ Background task started: Auto-OFF inactive machines (1 min timeout)")

if __name__ == "__main__":
    import uvicorn
    print(f"🚀 Starting WebSocket server on http://localhost:{PORT}")
    print(f"📡 WebSocket endpoint: ws://localhost:{PORT}/ws")
    print(f"🔌 REST API endpoint: http://localhost:{PORT}/")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
