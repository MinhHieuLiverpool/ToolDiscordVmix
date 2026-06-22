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

# Import config from parent directory if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    import config as _config
except ImportError:
    _config = None

if not MONGODB_URI:
    MONGODB_URI = getattr(_config, 'MONGODB_URI', 'mongodb://localhost:27017') if _config else 'mongodb://localhost:27017'

# Use database mobile_Monitor as requested
DATABASE_NAME = "mobile_Monitor"
COLLECTION_NAME = "logs"

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
        
        # Đặt id là IP máy (localIp), fallback sang wanIp hoặc unknown
        device_ip = payload_copy.get("localIp")
        if not device_ip or device_ip == "-":
            device_ip = payload_copy.get("wanIp") or "unknown"
            
        payload_copy["_id"] = device_ip
        if "timestamp" not in payload_copy:
            payload_copy["timestamp"] = datetime.now(VIETNAM_TZ).isoformat()
        
        # Ghi đè thay đổi giá trị của IP máy nếu đã tồn tại, ngược lại tạo mới
        collection.replace_one({"_id": device_ip}, payload_copy, upsert=True)
        return {"status": "success", "message": f"Log for {device_ip} saved/updated successfully"}
    except Exception as e:
        print(f"✗ Save mobile log error: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.get("/api/mobile-logs")
async def get_mobile_logs(limit: int = 100):
    try:
        logs = list(collection.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit))
        return {"status": "success", "data": logs}
    except Exception as e:
        print(f"✗ Get mobile logs error: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    uvicorn.run("server_mobile:app", host="0.0.0.0", port=port, reload=True)
