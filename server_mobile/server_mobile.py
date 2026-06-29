from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
import os
import sys
from datetime import datetime
import pytz
import uvicorn

# Configuration priority:
# 1) Environment variables (production-safe)
# 2) config.py values as fallback for local development
MONGODB_URI = os.getenv('MONGODB_URI', '').strip()
DATABASE_NAME = os.getenv('DATABASE_NAME', '').strip()
COLLECTION_NAME = os.getenv('COLLECTION_NAME', '').strip()

# Import config from parent directory if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    import config as _config
except ImportError:
    _config = None

if not MONGODB_URI:
    MONGODB_URI = getattr(_config, 'MONGODB_URI', 'mongodb://localhost:27017') if _config else 'mongodb://localhost:27017'
if not DATABASE_NAME:
    DATABASE_NAME = getattr(_config, 'DATABASE_NAME', 'vmix_monitor') if _config else 'vmix_monitor'
if not COLLECTION_NAME:
    # Default to 'mobile_logs' to prevent collision with desktop stream logs in 'logs' collection
    COLLECTION_NAME = "mobile_logs"

VIETNAM_TZ = pytz.timezone('Asia/Ho_Chi_Minh')

# MongoDB connection
try:
    mongo_kwargs = {
        "serverSelectionTimeoutMS": 10000,
    }
    if MONGODB_URI.startswith("mongodb+srv://"):
        mongo_kwargs["tls"] = True
        mongo_kwargs["tlsAllowInvalidCertificates"] = True
    client = MongoClient(MONGODB_URI, **mongo_kwargs)
    db = client[DATABASE_NAME]
    collection = db[COLLECTION_NAME]
    client.admin.command('ping')
    print(f"✓ Connected to MongoDB successfully! DB: {DATABASE_NAME}, Collection: {COLLECTION_NAME}")
except Exception as e:
    print(f"✗ MongoDB connection error: {e}")
    sys.exit(1)

app = FastAPI(title="Mobile Monitor Server")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status": "ok", "message": "Welcome to Mobile Monitor Server API"}

@app.post("/api/mobile-logs")
async def save_mobile_log(payload: dict):
    try:
        payload_copy = dict(payload)
        
        # Đặt id là deviceId, fallback sang IP máy (localIp), wanIp hoặc unknown
        device_id = payload_copy.get("deviceId")
        if not device_id or device_id == "-":
            device_id = payload_copy.get("localIp")
            if not device_id or device_id == "-":
                device_id = payload_copy.get("wanIp") or "unknown"
            
        payload_copy["_id"] = device_id
        # Luôn sử dụng thời gian nhận của server (UTC) để tránh lệch múi giờ / lệch kim đồng hồ trên thiết bị di động
        payload_copy["timestamp"] = datetime.now(pytz.utc).isoformat()
        
        # Sử dụng name_device mới từ payload nếu có, nếu không thì giữ nguyên giá trị cũ đã lưu trước đó trong DB
        payload_name = payload_copy.get("name_device", "").strip()
        if payload_name:
            payload_copy["name_device"] = payload_name
        else:
            existing = collection.find_one({"_id": device_id}, {"name_device": 1})
            if existing and "name_device" in existing:
                payload_copy["name_device"] = existing["name_device"]
            else:
                payload_copy["name_device"] = ""
        
        # Ghi đè thay đổi giá trị của thiết bị nếu đã tồn tại, ngược lại tạo mới
        collection.replace_one({"_id": device_id}, payload_copy, upsert=True)
        return {"status": "success", "message": f"Log for {device_id} saved/updated successfully"}
    except Exception as e:
        print(f"✗ Save mobile log error: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.patch("/api/mobile-logs/{device_id}")
async def update_device_name(device_id: str, payload: dict):
    try:
        name_device = payload.get("name_device")
        if name_device is None:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Missing 'name_device' in payload"})
        
        result = collection.update_one(
            {"_id": device_id},
            {"$set": {"name_device": name_device}}
        )
        if result.matched_count == 0:
            return JSONResponse(status_code=404, content={"status": "error", "message": "Device not found"})
        return {"status": "success", "message": "Device name updated successfully"}
    except Exception as e:
        print(f"✗ Update device name error: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.get("/api/mobile-logs")
async def get_mobile_logs(limit: int = 100):
    try:
        logs = list(collection.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit))
        return {"status": "success", "data": logs}
    except Exception as e:
        print(f"✗ Get mobile logs error: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

# Initialize collection for mobile game channel assignments
# (Note: we use the main server's game assignments directly)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    uvicorn.run("server_mobile:app", host="0.0.0.0", port=port, reload=True)
