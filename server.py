from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
from datetime import datetime
import pytz
from pymongo import MongoClient, DESCENDING
import os
import sys
from typing import List

# Try to import from config.py
try:
    from config import MONGODB_URI, DATABASE_NAME, COLLECTION_NAME
except ImportError:
    MONGODB_URI = os.getenv('MONGODB_URI', '')
    DATABASE_NAME = os.getenv('DATABASE_NAME', 'vmix_monitor')
    COLLECTION_NAME = os.getenv('COLLECTION_NAME', 'logs')

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

def get_all_logs():
    """Get all logs from MongoDB - Compatible với format cũ"""
    try:
        # Sort theo last_updated (format cũ) hoặc timestamp
        documents = collection.find().sort("last_updated", DESCENDING).limit(200)
        entries = []
        
        for doc in documents:
            # Debug: Print first doc
            if len(entries) == 0:
                print(f"📋 First document from MongoDB:")
                print(f"  name: {doc.get('name', 'N/A')}")
                print(f"  ip: {doc.get('ip', 'N/A')}")
                print(f"  ipwan: {doc.get('ipwan', 'N/A')}")
                print(f"  port: {doc.get('port', 'N/A')}")
                print(f"  status: {doc.get('status', 'N/A')}")
            
            # Format lại để tương thích với GUI
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
        
        return entries
    except Exception as e:
        print(f"Error getting logs: {e}")
        return []

@app.get("/")
async def get_all_data():
    """GET endpoint - lấy tất cả dữ liệu"""
    return JSONResponse(content=get_all_logs())

@app.post("/")
async def receive_data(data: dict):
    """Nhận dữ liệu từ vMix"""
    try:
        timestamp = datetime.now(VIETNAM_TZ).isoformat()
        
        # Lấy name làm key để identify máy
        machine_name = data.get('name', data.get('ip', 'Unknown'))
        
        # Kiểm tra document cũ để phát hiện thay đổi
        existing = collection.find_one({"name": machine_name})
        has_changes = False
        changed_fields = []
        
        if existing:
            # So sánh từng field quan trọng
            fields_to_check = ['ip', 'ipwan', 'status', 'port', 'name', 'statusapp']
            for field in fields_to_check:
                old_value = existing.get(field)
                new_value = data.get(field)
                if old_value != new_value:
                    has_changes = True
                    changed_fields.append(f"{field}: {old_value} → {new_value}")
        else:
            has_changes = True
            changed_fields.append("New machine added")
        
        # Cập nhật hoặc insert document
        document = {
            "name": machine_name,
            "ip": data.get('ip', ''),
            "ipwan": data.get('ipwan', ''),
            "status": data.get('status', 'UNKNOWN'),
            "port": data.get('port', ''),
            "statusapp": data.get('statusapp', 0),
            "last_updated": timestamp,
            "timestamp": timestamp
        }
        
        result = collection.update_one(
            {"name": machine_name},
            {"$set": document},
            upsert=True
        )
        
        # Nếu có thay đổi thì log và gửi Discord
        if has_changes:
            print(f"⚠ Changes detected for {machine_name}:")
            for change in changed_fields:
                print(f"  - {change}")
            
            # Gửi Discord notification
            if DISCORD_WEBHOOK and data.get('status'):
                send_discord_notification(
                    machine_name,
                    data.get('ipwan', 'Unknown'),
                    data.get('port', 'N/A'),
                    data.get('status', 'UNKNOWN')
                )
        
        # Broadcast update to all WebSocket clients
        await broadcast_updates()
        
        return JSONResponse(content={
            "status": "success",
            "message": f"Data received for {machine_name}",
            "changes_detected": has_changes,
            "modified": result.modified_count > 0
        })
    
    except Exception as e:
        print(f"✗ Error processing data: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

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
    """Broadcast updates to all connected WebSocket clients"""
    if not active_connections:
        return
    
    data = get_all_logs()
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

if __name__ == "__main__":
    import uvicorn
    print(f"🚀 Starting WebSocket server on http://localhost:{PORT}")
    print(f"📡 WebSocket endpoint: ws://localhost:{PORT}/ws")
    print(f"🔌 REST API endpoint: http://localhost:{PORT}/")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
