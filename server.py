from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import shutil
import subprocess
from datetime import datetime, timedelta
from collections import deque
import pytz
from bson import ObjectId
from pymongo import MongoClient, DESCENDING
import os
import sys
import hashlib
import hmac
from typing import List

try:
    import redis
except ImportError:
    redis = None

# Configuration priority:
# 1) Environment variables (production-safe)
# 2) config.py values as fallback for local development
MONGODB_URI = os.getenv('MONGODB_URI', '').strip()
DATABASE_NAME = os.getenv('DATABASE_NAME', '').strip()
COLLECTION_NAME = os.getenv('COLLECTION_NAME', '').strip()
DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK', '').strip()

try:
    import config as _config
except ImportError:
    _config = None

if not MONGODB_URI:
    MONGODB_URI = getattr(_config, 'MONGODB_URI', 'mongodb://localhost:27017') if _config else 'mongodb://localhost:27017'
if not DATABASE_NAME:
    DATABASE_NAME = getattr(_config, 'DATABASE_NAME', 'vmix_monitor') if _config else 'vmix_monitor'
if not COLLECTION_NAME:
    COLLECTION_NAME = getattr(_config, 'COLLECTION_NAME', 'logs') if _config else 'logs'
if not DISCORD_WEBHOOK:
    DISCORD_WEBHOOK = getattr(_config, 'DISCORD_WEBHOOK', '') if _config else ''



# Port configuration
PORT = int(os.getenv('PORT', 8001))
REDIS_URL = os.getenv('REDIS_URL', '').strip()
USE_TIMESERIES_STATS = os.getenv('USE_TIMESERIES_STATS', '1').strip().lower() in ('1', 'true', 'yes', 'on')
STATISTICS_TS_COLLECTION = os.getenv('STATISTICS_TS_COLLECTION', 'statistics_ts').strip() or 'statistics_ts'
_timeseries_available = False

# Timezone configuration - Vietnam
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
    selected_collection = db['selected_list']  # Collection mới cho selected list
    game_selected_collection = db['Game_Selected']  # Collection mới lưu cấu hình game đã chọn
    accounts_collection = db['web_accounts']
    roles_collection = db['web_roles']
    statistics_collection = db['statistics']
    statistics_ts_collection = db[STATISTICS_TS_COLLECTION]
    statistics_hours_collection = db['statistic_hours']
    
    # WAN IP Bandwidth Collection
    bandwidth_collection = db['bandwidth_statistic']
    
    # Shared Web Configurations Collection
    shared_web_configs_collection = db['shared_web_configs']
    debug_logs_collection = db['debug_logs']
    
    accounts_collection.create_index("username_key", unique=True)
    roles_collection.create_index("role_key", unique=True)
    statistics_collection.create_index("id", unique=True)
    bandwidth_collection.create_index([("ipwan", 1), ("date", 1)], unique=True)
    shared_web_configs_collection.create_index("uuid", unique=True)
    debug_logs_collection.create_index("debug_logged_at")


    if USE_TIMESERIES_STATS:
        existing_collections = set(db.list_collection_names())
        if STATISTICS_TS_COLLECTION not in existing_collections:
            try:
                db.create_collection(
                    STATISTICS_TS_COLLECTION,
                    timeseries={
                        "timeField": "ts",
                        "metaField": "meta",
                        "granularity": "seconds",
                    },
                )
                statistics_ts_collection = db[STATISTICS_TS_COLLECTION]
                print(f"✓ Created time series collection: {STATISTICS_TS_COLLECTION}")
            except Exception as ts_create_error:
                print(f"⚠ Time series create failed ({STATISTICS_TS_COLLECTION}): {ts_create_error}")
        try:
            statistics_ts_collection.create_index([("meta.id", 1), ("ts", -1)])
            _timeseries_available = True
        except Exception as ts_index_error:
            print(f"⚠ Time series index failed ({STATISTICS_TS_COLLECTION}): {ts_index_error}")
    # statistic_hours lưu 1 document / id, data là mảng các điểm avg 10 phút
    statistics_hours_collection.create_index("id")
    statistics_hours_collection.create_index("updated_at")
    client.admin.command('ping')
    if USE_TIMESERIES_STATS and _timeseries_available:
        print(f"✓ Time series statistics enabled: {STATISTICS_TS_COLLECTION}")
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

# Redis cache (optional)
_redis_client = None
_redis_enabled = False
_redis_stats_key_prefix = "stats:raw:"
_redis_stats_updated_key_prefix = "stats:updated:"
_redis_stats_ids_key = "stats:ids"
_redis_stat_hours_key_prefix = "stats:hours:"
_redis_stat_hours_ids_key = "stats:hours:ids"
_redis_stats_max_points = int(os.getenv("STATS_MAX_POINTS", "300"))

# ── In-memory cache ─────────────────────────────────────────────────────────────────
# Key: machine_name, Value: document dict
_data_cache: dict = {}

# Cache for WAN IP bandwidth stats of the current day
# Key: ipwan, Value: { "date": "DD-MM-YYYY", "sender_max": float, "receiver_max": float, "sender_min": float, "receiver_min": float }
_ipwan_bandwidth_cache: dict = {}


# Realtime statistics fallback cache.
# Key: statistics_id, Value: deque of samples [{cpu, ram, time}, ...]
_realtime_stats_cache: dict = {}
_realtime_stats_updated: dict = {}
_realtime_stats_max_points = int(os.getenv("REALTIME_STATS_MAX_POINTS", "300"))
_mongo_stats_max_points = int(os.getenv("MONGO_STATS_MAX_POINTS", "300"))
_stats_default_limit = int(os.getenv("STATS_DEFAULT_LIMIT", "60"))
_stats_response_max_limit = int(os.getenv("STATS_RESPONSE_MAX_LIMIT", "200"))
_stats_flush_interval_sec = max(1, int(os.getenv("STATS_FLUSH_INTERVAL_SEC", "5")))
_stats_flush_max_age_sec = max(_stats_flush_interval_sec, int(os.getenv("STATS_FLUSH_MAX_AGE_SEC", "20")))

# ── Tiered rollup configuration & buffers ──────────────────────────────────────────
# Tier: Raw(3min) → 1-min avg(5min) → 5-min avg(15min) → 15-min avg → statistic_hours
_TIER_RAW_WINDOW_SEC = int(os.getenv("TIER_RAW_WINDOW_SEC", "180"))    # 3 minutes
_TIER_1M_MAX_AGE_SEC = int(os.getenv("TIER_1M_MAX_AGE_SEC", "300"))    # keep 1-min avgs for 5 min
_TIER_5M_MAX_AGE_SEC = int(os.getenv("TIER_5M_MAX_AGE_SEC", "900"))    # keep 5-min avgs for 15 min
_TIERED_ROLLUP_INTERVAL_SEC = int(os.getenv("TIERED_ROLLUP_INTERVAL_SEC", "15"))
# {statistics_id: [{window_start, window_end, avg_cpu, avg_ram, avg_gpu, samples, cpu_points, ram_points, gpu_points, calculated_at}, ...]}
_stats_1m_buffer: dict = {}
_stats_5m_buffer: dict = {}
_app_started_at_utc = datetime.now(pytz.UTC)


def _parse_statistics_id(statistics_id: str):
    """Parse statistics id in format ip:port and return (ip, port_text, port_int_or_none)."""
    raw = str(statistics_id or "").strip()
    if not raw or ":" not in raw:
        return "", "", None
    ip_text, port_text = raw.rsplit(":", 1)
    ip_text = ip_text.strip()
    port_text = port_text.strip()
    try:
        port_int = int(port_text)
    except (TypeError, ValueError):
        port_int = None
    return ip_text, port_text, port_int


def _build_statistics_id(ip_value, port_value, fallback_name: str) -> str:
    ip_text = str(ip_value or "").strip()
    port_text = str(port_value or "").strip()
    if ip_text or port_text:
        return f"{ip_text}:{port_text}"
    return fallback_name


def _normalize_payload_list(raw_value):
    """Normalize payload field to list (accept dict for backward compatibility)."""
    if isinstance(raw_value, dict):
        return [raw_value]
    if isinstance(raw_value, list):
        return raw_value
    return []

# Removed SeaTalk webhook from server.py (notifications handled by server_gui_advanced)


def send_discord_notification(machine_name: str, ipwan: str, srt_name: str, port: str, status: str,
                               quality: str = "", srt_type: str = "", hostname: str = ""):
    """Gửi notification lên Discord & SeaTalk (đọc từ settings.json)"""
    import json
    import os
    import requests
    
    webhooks = []
    prefix = "SRT"
    fpath = "C:\\VmixMonitor\\Setting\\settings.json"
    if os.path.exists(fpath):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                saved = json.load(f)
            if isinstance(saved, dict):
                if "webhooks" in saved:
                    webhooks = saved["webhooks"]
                elif "webhook" in saved and saved["webhook"]:
                    webhooks = [{"type": "Discord", "url": saved["webhook"]}]
                if "prefix" in saved and saved["prefix"]:
                    prefix = saved["prefix"].strip()
        except Exception as e:
            print(f"⚠ Server: Error reading settings.json: {e}")
            
    if not webhooks:
        if DISCORD_WEBHOOK:
            webhooks = [{"type": "Discord", "url": DISCORD_WEBHOOK}]
        else:
            return

    label = srt_name if srt_name else machine_name

    for w_item in webhooks:
        w_type = w_item.get("type", "Discord")
        w_url = w_item.get("url", "").strip()
        if not w_url:
            continue

        if w_type == "Discord":
            try:
                parts = [f"[{prefix}][{label}] SRT {status} | IPWAN: {ipwan} | PORT: {port}"]
                if srt_type:
                    parts.append(f"Type: {srt_type}")
                if hostname:
                    parts.append(f"Host: {hostname}")
                if quality:
                    parts.append(f"Quality: {quality}")
                message = " | ".join(parts)
                payload = {"content": message}
                
                response = requests.post(w_url, json=payload, timeout=5)
                if response.status_code in [200, 204]:
                    print(f"✓ Discord notification sent for {label} to {w_url[:30]}...")
                else:
                    print(f"⚠ Discord webhook failed for {w_url[:30]}...: {response.status_code}")
            except Exception as e:
                print(f"✗ Discord notification error for {w_url[:30]}...: {e}")
        elif w_type == "Seatalk":
            try:
                parts = [f"**[{prefix}][{label}]** SRT {status}\nIPWAN: {ipwan} | PORT: {port}"]
                if srt_type:
                    parts.append(f"Type: {srt_type}")
                if hostname:
                    parts.append(f"Host: {hostname}")
                if quality:
                    parts.append(f"Quality: {quality}")
                content = "\n".join(parts)
                
                payload = {
                    "tag": "markdown",
                    "markdown": {
                        "content": content
                    }
                }
                response = requests.post(w_url, json=payload, timeout=5)
                if response.status_code == 200:
                    print(f"✓ SeaTalk notification sent for {label} to {w_url[:30]}...")
                else:
                    print(f"⚠ SeaTalk webhook failed for {w_url[:30]}...: {response.status_code}")
            except Exception as e:
                print(f"✗ SeaTalk notification error for {w_url[:30]}...: {e}")

def get_all_logs():
    """Lấy tất cả logs từ in-memory cache để đạt hiệu năng cao nhất"""
    entries = []
    # Sắp xếp theo last_updated giảm dần
    sorted_items = sorted(_data_cache.values(), key=lambda x: x.get("last_updated", ""), reverse=True)
    for doc in sorted_items:
        entries.append({
            "timestamp": doc.get("last_updated", ""),
            "data": doc
        })
    return entries


def _to_json_safe(value):
    """Convert values to JSON-safe payload (notably MongoDB ObjectId)."""
    return jsonable_encoder(
        value,
        custom_encoder={ObjectId: str},
        exclude={"_id"},
    )


def _build_health_payload() -> dict:
    """Create a lightweight health payload without external I/O."""
    now_utc = datetime.now(pytz.UTC)
    uptime_seconds = int((now_utc - _app_started_at_utc).total_seconds())
    return {
        "status": "ok",
        "service": "vmix-monitor-server",
        "uptime_seconds": uptime_seconds,
        "server_time_utc": now_utc.isoformat(),
        "machines_cached": len(_data_cache),
        "websocket_clients": len(active_connections),
    }

@app.api_route("/", methods=["GET", "HEAD"])
async def health_check():
    """Health check endpoint for UptimeRobot - hỗ trợ cả GET và HEAD"""
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("I am Hieu Liverpool!")


@app.api_route("/health", methods=["GET", "HEAD"])
async def health_endpoint():
    """Primary lightweight health endpoint for Render/UptimeRobot."""
    return JSONResponse(content=_build_health_payload())


@app.api_route("/healthz", methods=["GET", "HEAD"])
async def healthz_endpoint():
    """Alias of /health for compatibility with common probe defaults."""
    return JSONResponse(content=_build_health_payload())

@app.get("/logs")
async def get_all_data():
    """GET endpoint - lấy tất cả dữ liệu"""
    return JSONResponse(content=_to_json_safe(get_all_logs()))

@app.get("/load_debug_logs")
async def load_debug_logs():
    """Load toàn bộ debug logs từ database"""
    try:
        loop = asyncio.get_event_loop()
        documents = await loop.run_in_executor(
            None,
            lambda: list(debug_logs_collection.find().sort("debug_logged_at", -1))
        )
        for doc in documents:
            doc.pop('_id', None)
        return JSONResponse(content=_to_json_safe(documents))
    except Exception as e:
        print(f"✗ Load debug logs error: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/download_debug_logs")
async def download_debug_logs(timeStart: str = None, timeEnd: str = None, timestart: str = None, timeend: str = None):
    """Tải xuống toàn bộ hoặc một phần debug logs theo khoảng thời gian dưới dạng file .txt"""
    try:
        # Normalize parameter names
        t_start = timeStart or timestart
        t_end = timeEnd or timeend
        
        query_filter = {}
        
        def parse_time_param(param_str: str) -> str:
            if not param_str:
                return None
            param_str = param_str.strip()
            # Check if it's already a full ISO string (contains '-' and 'T')
            if '-' in param_str and 'T' in param_str:
                try:
                    dt = datetime.fromisoformat(param_str)
                    if dt.tzinfo is None:
                        dt = VIETNAM_TZ.localize(dt)
                    return dt.astimezone(VIETNAM_TZ).isoformat()
                except ValueError:
                    pass
            
            # Otherwise try parsing as HH:MM:SS or HH:MM of the current day
            try:
                parts = param_str.split(':')
                hrs = int(parts[0])
                mins = int(parts[1]) if len(parts) > 1 else 0
                secs = int(parts[2]) if len(parts) > 2 else 0
                now_vn = datetime.now(VIETNAM_TZ)
                dt = now_vn.replace(hour=hrs, minute=mins, second=secs, microsecond=0)
                # Heuristic: if parsed time is in the future, it must be from yesterday
                if dt > now_vn:
                    dt = dt - timedelta(days=1)
                return dt.isoformat()
            except (ValueError, IndexError):
                pass
            return None

        start_iso = parse_time_param(t_start)
        end_iso = parse_time_param(t_end)

        if start_iso or end_iso:
            time_filter = {}
            if start_iso:
                time_filter["$gte"] = start_iso
            if end_iso:
                time_filter["$lte"] = end_iso
            query_filter["debug_logged_at"] = time_filter

        print(f"📥 [DOWNLOAD] Filter time range query: {query_filter}")

        loop = asyncio.get_event_loop()
        documents = await loop.run_in_executor(
            None,
            lambda: list(debug_logs_collection.find(query_filter).sort("debug_logged_at", 1))
        )
        
        lines = []
        for doc in documents:
            logged_at_str = doc.get("debug_logged_at", doc.get("timestamp", ""))
            try:
                dt = datetime.fromisoformat(logged_at_str)
                if dt.tzinfo is None:
                    dt = VIETNAM_TZ.localize(dt)
                dt = dt.astimezone(VIETNAM_TZ)
                time_str = dt.strftime("%H:%M:%S")
                date_str = dt.strftime("%d/%m/%Y")
                format_time_date = f"[ {time_str} - {date_str} ]"
            except Exception:
                format_time_date = "[ --:--:-- - --/--/---- ]"

            machine_name = doc.get('name', 'Unknown')
            ip = doc.get('ip', '-') or '-'
            ipwan = doc.get('ipwan', '-') or '-'
            
            raw_doc = dict(doc)
            raw_doc.pop('_id', None)
            raw_doc.pop('debug_logged_at', None)
            raw_doc.pop('timestamp', None)
            
            json_payload = json.dumps(_to_json_safe(raw_doc), ensure_ascii=False)
            
            log_line = f"{format_time_date} - {machine_name} - {ip} - {ipwan} - {json_payload}"
            lines.append(log_line)
            
        txt_content = "\n".join(lines)
        
        from fastapi.responses import Response
        filename = f"debug_logs_{datetime.now(VIETNAM_TZ).strftime('%Y%m%d_%H%M%S')}.txt"
        return Response(
            content=txt_content,
            media_type="text/plain",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        print(f"✗ Download debug logs error: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)



@app.get("/bandwidth")
async def get_bandwidth_stats(date: str = None):
    """Lấy dữ liệu băng thông của các IP WAN cho một ngày (DD-MM-YYYY)"""
    try:
        if not date:
            date = datetime.now(VIETNAM_TZ).strftime("%d-%m-%Y")
        
        loop = asyncio.get_event_loop()
        docs = await loop.run_in_executor(
            None,
            lambda: list(bandwidth_collection.find({"date": date}))
        )
        
        for doc in docs:
            doc.pop("_id", None)
            
        return JSONResponse(content=_to_json_safe(docs))
    except Exception as e:
        print(f"✗ Get bandwidth stats error: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


def _zero_out_metrics_if_offline(doc: dict):
    """Clean all metrics to 0 or OFF when the app is offline (statusapp != 1)"""
    if doc.get("statusapp", 0) != 1:
        doc["ping"] = 0
        doc["ping_timeouts"] = 0
        doc["temperature"] = 0
        doc["cpu"] = 0
        doc["ram"] = 0
        doc["memory"] = 0
        doc["gpu"] = 0
        doc["sender_mbps"] = 0
        doc["receiver_mbps"] = 0
        doc["vmixsend"] = 0
        doc["vmixreceive"] = 0
        doc["vmix_recording"] = False
        doc["vmix_streaming"] = False
        doc["vmix_external"] = False
        doc["vmix_multicorder"] = False
        doc["MultirecordingStatus"] = False
        doc["List_REcord"] = []
        doc["ListMultiREcord"] = []
        doc["ListMultiRecord"] = []
        doc["PIDVMIX"] = ""
        doc["ffmpeg"] = []
        
        # Set all SRT streams to OFF
        srt_list = doc.get("SRT", [])
        if isinstance(srt_list, list):
            for srt_item in srt_list:
                if isinstance(srt_item, dict):
                    srt_item["status"] = "OFF"
    return doc


@app.post("/")
async def receive_data(data: dict):
    """Nhận dữ liệu từ vMix"""
    try:
        timestamp = datetime.now(VIETNAM_TZ).isoformat()
        machine_name = data.get('name', data.get('ip', 'Unknown'))

        # ── 0. Ghi logs debug ra C:\VmixMonitor\debugger\<ngày>.txt ──
        try:
            now_dt = datetime.now(VIETNAM_TZ)
            today_str = now_dt.strftime("%Y-%m-%d")
            debug_dir = r"C:\VmixMonitor\debugger"
            os.makedirs(debug_dir, exist_ok=True)
            log_file = os.path.join(debug_dir, f"{today_str}.txt")
            
            time_str = now_dt.strftime("%H:%M:%S")
            date_str = now_dt.strftime("%d/%m/%Y")
            format_time_date = f"[ {time_str} - {date_str} ]"
            
            log_line = f"{format_time_date} - {machine_name} - {data.get('ip', '-')} - {data.get('ipwan', '-')} - {json.dumps(data, ensure_ascii=False)}\n"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_line)
        except Exception as log_err:
            print(f"✗ Error writing local file debug log: {log_err}")

        # Extract SRT/stream/stream_keys as arrays (backward compat: accept dict too)
        srt_list = _normalize_payload_list(data.get('SRT', []))
        stream_list = _normalize_payload_list(data.get('stream', []))
        stream_keys_list = _normalize_payload_list(data.get('stream_keys', []))

        # ── 1. Cập nhật cache ngay lập tức (<1ms, không block) ──
        prev = _data_cache.get(machine_name, {})
        document = {
            "name":        machine_name,
            "name_edit":   prev.get("name_edit", ""),
            "ip":          data.get('ip', ''),
            "ipwan":       data.get('ipwan', ''),
            "statusapp":   data.get('statusapp', 0),
            "ping":        data.get('ping'),
            "ping_timeouts": data.get('ping_timeouts', 0),
            "temperature": data.get('temperature', data.get('cpu')),
            "memory":      data.get('memory', data.get('ram')),
            "gpu":         data.get('gpu', data.get('gpu_percent')),
            "sender_mbps": data.get('sender_mbps'),
            "receiver_mbps": data.get('receiver_mbps'),
            "mac_address": data.get('mac_address'),
            "network_speed": data.get('network_speed'),
            "vmixsend": data.get('vmixsend'),
            "vmixreceive": data.get('vmixreceive'),
            "PIDVMIX": data.get('PIDVMIX', ''),
            "vmix_recording": data.get('vmix_recording', False),
            "vmix_streaming": data.get('vmix_streaming', False),
            "vmix_external":  data.get('vmix_external', False),
            "vmix_multicorder": data.get('vmix_multicorder', False),
            "MultirecordingStatus": data.get('MultirecordingStatus', False),
            "List_REcord": data.get('List_REcord', []),
            "ListMultiREcord": data.get('ListMultiREcord', data.get('ListMultiRecord', [])),
            "resolution":     data.get('resolution', '—'),
            "SRT": srt_list,
            "stream": stream_list,
            "stream_keys": stream_keys_list,
            "ffmpeg": _normalize_payload_list(data.get('ffmpeg', [])),
            "last_updated": timestamp,
            "timestamp":   timestamp,
        }
        _zero_out_metrics_if_offline(document)
        _data_cache[machine_name] = document

        # WAN IP Bandwidth peak monitoring
        ipwan = data.get('ipwan', '')
        if ipwan:
            async def process_ipwan_peak():
                try:
                    today_str = datetime.now(VIETNAM_TZ).strftime("%d-%m-%Y")
                    cached = await _async_get_cached_ipwan_stats(ipwan, today_str)
                    total_sender, total_receiver = _get_ipwan_totals(ipwan)
                    
                    # Update min values in cache if active (> 0)
                    if total_sender > 0.0 and (cached["sender_min"] == 0.0 or total_sender < cached["sender_min"]):
                        cached["sender_min"] = total_sender
                    if total_receiver > 0.0 and (cached["receiver_min"] == 0.0 or total_receiver < cached["receiver_min"]):
                        cached["receiver_min"] = total_receiver

                    # Check for peak override
                    is_peak = False
                    if total_sender > cached["sender_max"]:
                        cached["sender_max"] = total_sender
                        is_peak = True
                    if total_receiver > cached["receiver_max"]:
                        cached["receiver_max"] = total_receiver
                        is_peak = True
                        
                    if is_peak:
                        print(f"🔥 [PEAK DETECTED] {ipwan} - Sender: {total_sender} Mbps (Max: {cached['sender_max']}), Receiver: {total_receiver} Mbps (Max: {cached['receiver_max']})")
                        await _mongo_upsert_ipwan_bandwidth(
                            ipwan=ipwan,
                            today_str=today_str,
                            sender=total_sender,
                            receiver=total_receiver,
                            sender_max=cached["sender_max"],
                            receiver_max=cached["receiver_max"],
                            sender_min=cached["sender_min"],
                            receiver_min=cached["receiver_min"],
                            timestamp=timestamp,
                            push_history=True
                        )
                except Exception as ex:
                    print(f"✗ Error processing IP WAN peak for {ipwan}: {ex}")

            asyncio.create_task(process_ipwan_peak())


        ip_val = data.get('ip', '')
        statistics_id = _build_statistics_id(ip_val, data.get('port', ''), machine_name)

        # Compare SRT status changes for Discord + SeaTalk notifications
        prev_srt_list = _normalize_payload_list(prev.get('SRT', []))
        prev_stream_list = _normalize_payload_list(prev.get('stream', []))
        prev_stream_keys_list = _normalize_payload_list(prev.get('stream_keys', []))
        prev_srt_map = {str(s.get('port', '')).strip(): s for s in prev_srt_list if isinstance(s, dict)}
        for srt_item in srt_list:
            if not isinstance(srt_item, dict):
                continue
            port_val = str(srt_item.get('port', '')).strip()
            if not port_val or port_val in ('-', '—', 'None', 'null'):
                continue
            new_status = srt_item.get('status', '')
            prev_srt_entry = prev_srt_map.get(port_val, {})
            old_status = prev_srt_entry.get('status', '')
            if old_status and old_status != new_status and new_status in ('ON', 'OFF'):
                srt_name = srt_item.get('nameSRT', '')
                srt_quality = srt_item.get('quality', '')
                srt_type = srt_item.get('type', '')
                srt_hostname = srt_item.get('hostname', '')
                send_discord_notification(machine_name, data.get('ipwan', ''), srt_name, port_val, new_status,
                                          quality=srt_quality, srt_type=srt_type, hostname=srt_hostname)

        # Check for general field changes
        fields_to_check = ['ip', 'ipwan']
        has_changes = not prev or any(
            prev.get(f) != document.get(f) for f in fields_to_check
        ) or str(prev_srt_list) != str(srt_list) or str(prev_stream_list) != str(stream_list) or str(prev_stream_keys_list) != str(stream_keys_list)
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
            "statistics_id": statistics_id,
        })

    except Exception as e:
        print(f"✗ Error processing data: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


async def _async_get_cached_ipwan_stats(ipwan: str, today_str: str) -> dict:
    """Get or load/initialize the bandwidth cache entry asynchronously."""
    cached = _ipwan_bandwidth_cache.get(ipwan)
    if cached and cached.get("date") == today_str:
        return cached

    doc_id = f"{ipwan}_{today_str}"
    loop = asyncio.get_event_loop()
    try:
        doc = await loop.run_in_executor(
            None,
            lambda: bandwidth_collection.find_one({"_id": doc_id})
        )
        if doc:
            entry = {
                "date": today_str,
                "sender_max": float(doc.get("sender_max", 0.0)),
                "receiver_max": float(doc.get("receiver_max", 0.0)),
                "sender_min": float(doc.get("sender_min", 0.0)),
                "receiver_min": float(doc.get("receiver_min", 0.0))
            }
        else:
            entry = {
                "date": today_str,
                "sender_max": 0.0,
                "receiver_max": 0.0,
                "sender_min": 0.0,
                "receiver_min": 0.0
            }
    except Exception as e:
        print(f"✗ Error loading WAN IP stats from MongoDB: {e}")
        entry = {
            "date": today_str,
            "sender_max": 0.0,
            "receiver_max": 0.0,
            "sender_min": 0.0,
            "receiver_min": 0.0
        }

    _ipwan_bandwidth_cache[ipwan] = entry
    return entry


def _get_ipwan_totals(ipwan: str) -> tuple:
    """Calculate total sender_mbps and receiver_mbps for all active machines sharing the same ipwan."""
    if not ipwan:
        return 0.0, 0.0

    total_sender = 0.0
    total_receiver = 0.0
    now_vn = datetime.now(VIETNAM_TZ)
    # A machine is considered active if it sent updates in the last 1 minute
    cutoff = now_vn - timedelta(minutes=1)

    for doc in _data_cache.values():
        if not isinstance(doc, dict):
            continue
        if doc.get("ipwan") != ipwan:
            continue
        if doc.get("statusapp", 0) != 1:
            continue

        last_up_str = str(doc.get("last_updated", "") or "")
        if not last_up_str:
            continue

        try:
            last_up = datetime.fromisoformat(last_up_str)
            if last_up.tzinfo is None:
                last_up = VIETNAM_TZ.localize(last_up)
            last_up = last_up.astimezone(VIETNAM_TZ)
            
            if last_up >= cutoff:
                sender_val = doc.get("sender_mbps")
                receiver_val = doc.get("receiver_mbps")
                
                try:
                    total_sender += float(sender_val) if sender_val is not None else 0.0
                except (ValueError, TypeError):
                    pass
                try:
                    total_receiver += float(receiver_val) if receiver_val is not None else 0.0
                except (ValueError, TypeError):
                    pass
        except Exception:
            continue

    return round(total_sender, 2), round(total_receiver, 2)


async def _mongo_upsert_ipwan_bandwidth(ipwan: str, today_str: str, sender: float, receiver: float, sender_max: float, receiver_max: float, sender_min: float, receiver_min: float, timestamp: str, push_history: bool):
    """Write/Update the IP WAN bandwidth document in MongoDB."""
    doc_id = f"{ipwan}_{today_str}"
    
    update_query = {
        "$set": {
            "ipwan": ipwan,
            "date": today_str,
            "sender_max": sender_max,
            "receiver_max": receiver_max,
            "sender_min": sender_min,
            "receiver_min": receiver_min,
            "last_updated": timestamp
        }
    }
    
    if push_history:
        update_query["$push"] = {
            "history": {
                "$each": [{
                    "timestamp": timestamp,
                    "sender": sender,
                    "receiver": receiver
                }],
                "$slice": -500  # limit history list to 500 items
            }
        }
        
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(
            None,
            lambda: bandwidth_collection.update_one(
                {"_id": doc_id},
                update_query,
                upsert=True
            )
        )
    except Exception as e:
        print(f"✗ MongoDB IP WAN bandwidth upsert error ({ipwan}): {e}")




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

async def _mongo_append_statistics(statistics_id: str, cpu_value, ram_value, gpu_value, timestamp: str):
    """Append CPU/RAM/GPU sample to statistics collection and keep a bounded history."""
    sample = {
        "cpu": cpu_value,
        "ram": ram_value,
        "gpu": gpu_value,
        "time": timestamp,
    }

    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(
            None,
            lambda: statistics_collection.update_one(
                {"id": statistics_id},
                {
                    "$set": {"updated_at": timestamp},
                    "$push": {"data": {"$each": [sample], "$slice": -_mongo_stats_max_points}},
                },
                upsert=True,
            )
        )
    except Exception as e:
        print(f"✗ MongoDB statistics append error ({statistics_id}): {e}")


async def _mongo_append_ping(statistics_id: str, ping_value, timestamp: str):
    """Append ping sample to ping_history collection and keep a bounded history."""
    try:
        if ping_value is not None and ping_value != "—" and ping_value != "":
            ping_val = float(ping_value)
        else:
            ping_val = None
    except (TypeError, ValueError):
        ping_val = None

    loop = asyncio.get_event_loop()
    try:
        # Fetch the last sample from the history to prevent duplicate or redundant null entries
        last_doc = await loop.run_in_executor(
            None,
            lambda: db['ping_history'].find_one(
                {"id": statistics_id},
                {"_id": 0, "data": {"$slice": -1}}
            )
        )

        if last_doc and "data" in last_doc and len(last_doc["data"]) > 0:
            last_sample = last_doc["data"][0]
            last_ping = last_sample.get("ping")
            last_time_str = last_sample.get("time", "")

            # If both current and last recorded pings are None (stale/offline), skip appending
            if ping_val is None and last_ping is None:
                return

            # Rate limit database writes to prevent duplicates in multi-worker environments
            if last_time_str:
                try:
                    last_time = datetime.fromisoformat(last_time_str)
                    now_vn = datetime.now(VIETNAM_TZ)
                    if last_time.tzinfo is None:
                        last_time = VIETNAM_TZ.localize(last_time)
                    last_time = last_time.astimezone(VIETNAM_TZ)
                    if (now_vn - last_time).total_seconds() < 8.0:
                        return
                except Exception:
                    pass

        sample = {
            "ping": ping_val,
            "time": timestamp,
        }

        await loop.run_in_executor(
            None,
            lambda: db['ping_history'].update_one(
                {"id": statistics_id},
                {
                    "$set": {"updated_at": timestamp},
                    "$push": {"data": {"$each": [sample], "$slice": -300}},
                },
                upsert=True,
            )
        )
    except Exception as e:
        print(f"✗ MongoDB ping append error ({statistics_id}): {e}")


async def _mongo_insert_statistics_ts(statistics_id: str, cpu_value, ram_value, gpu_value, timestamp: str):
    """Insert one CPU/RAM/GPU sample into MongoDB time series collection."""
    if not USE_TIMESERIES_STATS or not _timeseries_available:
        return

    sample_dt = _parse_sample_time(timestamp)
    if sample_dt is None:
        sample_dt = datetime.now(VIETNAM_TZ)

    # Keep a stable text timestamp for existing frontend parsing while using a Date for time series indexing.
    sample_doc = {
        "meta": {"id": statistics_id},
        "ts": sample_dt.astimezone(pytz.UTC),
        "time": timestamp,
        "cpu": cpu_value,
        "ram": ram_value,
        "gpu": gpu_value,
    }

    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(
            None,
            lambda: statistics_ts_collection.insert_one(sample_doc)
        )
    except Exception as e:
        print(f"⚠ MongoDB time series insert error ({statistics_id}): {e}")


async def _mongo_get_statistics_ts(statistics_id: str, limit: int):
    """Read latest CPU/RAM samples from MongoDB time series collection."""
    if not USE_TIMESERIES_STATS or not _timeseries_available:
        return None

    loop = asyncio.get_event_loop()

    def _worker():
        rows = list(
            statistics_ts_collection
            .find(
                {"meta.id": statistics_id},
                {"_id": 0, "cpu": 1, "ram": 1, "gpu": 1, "time": 1, "ts": 1},
            )
            .sort("ts", DESCENDING)
            .limit(limit)
        )

        if not rows:
            return None

        rows.reverse()
        data = []
        for row in rows:
            time_text = str(row.get("time", "") or "")
            if not time_text:
                ts_val = row.get("ts")
                if isinstance(ts_val, datetime):
                    if ts_val.tzinfo is None:
                        ts_val = pytz.UTC.localize(ts_val)
                    time_text = ts_val.astimezone(VIETNAM_TZ).isoformat()

            data.append({
                "cpu": row.get("cpu"),
                "ram": row.get("ram"),
                "gpu": row.get("gpu"),
                "time": time_text,
            })

        updated_at = data[-1].get("time", "") if data else ""
        return {"id": statistics_id, "data": data, "updated_at": updated_at}

    try:
        return await loop.run_in_executor(None, _worker)
    except Exception as e:
        print(f"⚠ MongoDB time series read error ({statistics_id}): {e}")
        return None


def _redis_key_stats_raw(statistics_id: str) -> str:
    return f"{_redis_stats_key_prefix}{statistics_id}"


def _redis_key_stats_updated(statistics_id: str) -> str:
    return f"{_redis_stats_updated_key_prefix}{statistics_id}"


def _redis_key_stat_hours(statistics_id: str) -> str:
    return f"{_redis_stat_hours_key_prefix}{statistics_id}"


def _redis_serialize(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _redis_deserialize(value):
    if value is None:
        return None
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    try:
        return json.loads(value)
    except Exception:
        return None


def _init_redis_cache():
    global _redis_client, _redis_enabled

    if not REDIS_URL:
        print("ℹ Redis disabled: REDIS_URL not set")
        return

    if redis is None:
        print("⚠ Redis package not installed, running without Redis cache")
        return

    try:
        client = redis.Redis.from_url(REDIS_URL, decode_responses=False, socket_timeout=1.5)
        client.ping()
        _redis_client = client
        _redis_enabled = True
        print(f"✓ Redis connected: {REDIS_URL}")
    except Exception as e:
        _redis_client = None
        _redis_enabled = False
        print(f"⚠ Redis unavailable ({REDIS_URL}): {e}")


async def _redis_append_statistics_sample(statistics_id: str, sample: dict, timestamp: str):
    if not _redis_enabled or _redis_client is None:
        return

    loop = asyncio.get_event_loop()

    def _worker():
        raw_key = _redis_key_stats_raw(statistics_id)
        _redis_client.rpush(raw_key, _redis_serialize(sample))
        _redis_client.ltrim(raw_key, -_redis_stats_max_points, -1)
        _redis_client.set(_redis_key_stats_updated(statistics_id), timestamp)
        _redis_client.sadd(_redis_stats_ids_key, statistics_id)

    try:
        await loop.run_in_executor(None, _worker)
    except Exception as e:
        print(f"⚠ Redis append sample failed ({statistics_id}): {e}")


async def _redis_get_statistics_doc(statistics_id: str):
    if not _redis_enabled or _redis_client is None:
        return None

    loop = asyncio.get_event_loop()

    def _worker():
        raw_key = _redis_key_stats_raw(statistics_id)
        items = _redis_client.lrange(raw_key, 0, -1)
        if not items:
            return None

        samples = []
        for item in items:
            parsed = _redis_deserialize(item)
            if isinstance(parsed, dict):
                samples.append(parsed)

        updated_raw = _redis_client.get(_redis_key_stats_updated(statistics_id))
        updated_at = updated_raw.decode("utf-8") if isinstance(updated_raw, bytes) else updated_raw
        return {"id": statistics_id, "data": samples, "updated_at": updated_at or ""}

    try:
        return await loop.run_in_executor(None, _worker)
    except Exception as e:
        print(f"⚠ Redis read statistics failed ({statistics_id}): {e}")
        return None


async def _redis_set_statistics_doc(statistics_id: str, samples: list, updated_at: str):
    if not _redis_enabled or _redis_client is None:
        return

    loop = asyncio.get_event_loop()

    def _worker():
        pipe = _redis_client.pipeline()
        raw_key = _redis_key_stats_raw(statistics_id)
        pipe.delete(raw_key)
        if samples:
            encoded = [_redis_serialize(s) for s in samples if isinstance(s, dict)]
            if encoded:
                pipe.rpush(raw_key, *encoded)
        pipe.set(_redis_key_stats_updated(statistics_id), updated_at or "")
        pipe.sadd(_redis_stats_ids_key, statistics_id)
        pipe.execute()

    try:
        await loop.run_in_executor(None, _worker)
    except Exception as e:
        print(f"⚠ Redis set statistics failed ({statistics_id}): {e}")


async def _redis_get_stat_hours_doc(statistics_id: str):
    if not _redis_enabled or _redis_client is None:
        return None

    loop = asyncio.get_event_loop()

    def _worker():
        raw = _redis_client.get(_redis_key_stat_hours(statistics_id))
        parsed = _redis_deserialize(raw)
        return parsed if isinstance(parsed, dict) else None

    try:
        return await loop.run_in_executor(None, _worker)
    except Exception as e:
        print(f"⚠ Redis read statistic_hours failed ({statistics_id}): {e}")
        return None


async def _redis_set_stat_hours_doc(statistics_id: str, doc: dict):
    if not _redis_enabled or _redis_client is None:
        return

    loop = asyncio.get_event_loop()

    def _worker():
        _redis_client.set(_redis_key_stat_hours(statistics_id), _redis_serialize(doc))
        _redis_client.sadd(_redis_stat_hours_ids_key, statistics_id)

    try:
        await loop.run_in_executor(None, _worker)
    except Exception as e:
        print(f"⚠ Redis set statistic_hours failed ({statistics_id}): {e}")


async def _redis_get_all_stat_hours_docs():
    if not _redis_enabled or _redis_client is None:
        return None

    loop = asyncio.get_event_loop()

    def _worker():
        ids = _redis_client.smembers(_redis_stat_hours_ids_key)
        if not ids:
            return []

        decoded_ids = [item.decode("utf-8") if isinstance(item, bytes) else str(item) for item in ids]
        keys = [_redis_key_stat_hours(stat_id) for stat_id in decoded_ids]
        values = _redis_client.mget(keys)
        docs = []
        for raw in values:
            parsed = _redis_deserialize(raw)
            if isinstance(parsed, dict):
                docs.append(parsed)
        return docs

    try:
        return await loop.run_in_executor(None, _worker)
    except Exception as e:
        print(f"⚠ Redis read all statistic_hours failed: {e}")
        return None


def _parse_sample_time(time_str):
    """Parse sample timestamp into Vietnam timezone datetime."""
    try:
        dt = datetime.fromisoformat(str(time_str))
        if dt.tzinfo is None:
            dt = VIETNAM_TZ.localize(dt)
        return dt.astimezone(VIETNAM_TZ)
    except Exception:
        return None


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _bucket_1m(dt: datetime):
    """Align datetime to 1-minute boundary."""
    return dt.replace(second=0, microsecond=0)


def _bucket_5m(dt: datetime):
    """Align datetime to 5-minute boundary."""
    return dt.replace(minute=(dt.minute // 5) * 5, second=0, microsecond=0)


def _bucket_15m(dt: datetime):
    """Align datetime to 15-minute boundary."""
    return dt.replace(minute=(dt.minute // 15) * 15, second=0, microsecond=0)


def _bucket_10m(dt: datetime):
    """Legacy: 10-minute boundary (kept for backward compat)."""
    return dt.replace(minute=(dt.minute // 10) * 10, second=0, microsecond=0)


def _merge_into_statistic_hours(statistics_id: str, new_rows: list, run_stamp: str):
    """Merge new rollup rows into statistic_hours collection (upsert by window_start)."""
    if not new_rows:
        return

    existing_doc = statistics_hours_collection.find_one(
        {"id": statistics_id},
        {"_id": 0, "data": 1}
    )
    existing_data = existing_doc.get("data", []) if existing_doc else []
    new_window_map = {row["window_start"]: row for row in new_rows}

    merged_data = []
    for item in existing_data:
        if not isinstance(item, dict):
            continue
        ws = item.get("window_start")
        if ws in new_window_map:
            merged_data.append(new_window_map.pop(ws))
        else:
            merged_data.append(item)

    if new_window_map:
        merged_data.extend(new_window_map.values())

    merged_data.sort(key=lambda x: x.get("window_start", ""))

    statistics_hours_collection.update_one(
        {"id": statistics_id},
        {
            "$set": {
                "id": statistics_id,
                "data": merged_data,
                "updated_at": run_stamp,
            }
        },
        upsert=True,
    )

    # Update Redis cache if available
    if _redis_enabled and _redis_client is not None:
        rolled_doc = {
            "id": statistics_id,
            "data": merged_data,
            "updated_at": run_stamp,
        }
        _redis_client.set(_redis_key_stat_hours(statistics_id), _redis_serialize(rolled_doc))
        _redis_client.sadd(_redis_stat_hours_ids_key, statistics_id)


async def _tiered_rollup():
    """
    Tiered rolling aggregation (cuốn chiếu):
      Raw (3 min) → 1-min averages (5 min) → 5-min averages (15 min) → statistic_hours

    Runs every 15 seconds. Does NOT touch the 3-minute realtime display buffer.
    """
    loop = asyncio.get_event_loop()
    now_vn = datetime.now(VIETNAM_TZ)
    run_stamp = now_vn.isoformat()

    raw_cutoff = now_vn - timedelta(seconds=_TIER_RAW_WINDOW_SEC)    # 3 min ago
    m1_cutoff  = now_vn - timedelta(seconds=_TIER_1M_MAX_AGE_SEC)    # 5 min ago
    m5_cutoff  = now_vn - timedelta(seconds=_TIER_5M_MAX_AGE_SEC)    # 15 min ago

    def _worker():
        tier1_total = 0
        tier2_total = 0
        tier3_total = 0

        # ══════════════════════════════════════════════════════════════
        # TIER 1: Raw samples → 1-minute averages
        # Process samples from MongoDB statistics collection that are
        # older than the 3-minute display window.
        # ══════════════════════════════════════════════════════════════
        mongo_docs = list(statistics_collection.find({}, {"_id": 0, "id": 1, "data": 1}))

        for doc in mongo_docs:
            statistics_id = doc.get("id", "")
            samples = doc.get("data", [])
            if not statistics_id or not isinstance(samples, list) or not samples:
                continue

            old_samples = []   # to aggregate into 1-min buckets
            remaining = []     # keep for realtime display

            for sample in samples:
                if not isinstance(sample, dict):
                    remaining.append(sample)
                    continue
                sample_dt = _parse_sample_time(sample.get("time"))
                if not sample_dt:
                    remaining.append(sample)
                    continue
                if sample_dt < raw_cutoff:
                    old_samples.append((sample_dt, sample))
                else:
                    remaining.append(sample)

            if not old_samples:
                continue

            # Group by 1-minute window
            minute_buckets = {}
            for sample_dt, sample in old_samples:
                bucket_start = _bucket_1m(sample_dt)
                bucket = minute_buckets.setdefault(bucket_start, {
                    "cpu_sum": 0.0, "cpu_count": 0,
                    "ram_sum": 0.0, "ram_count": 0,
                    "gpu_sum": 0.0, "gpu_count": 0,
                    "sample_count": 0,
                })
                cpu = _to_float(sample.get("cpu"))
                if cpu is not None:
                    bucket["cpu_sum"] += cpu
                    bucket["cpu_count"] += 1
                ram = _to_float(sample.get("ram"))
                if ram is not None:
                    bucket["ram_sum"] += ram
                    bucket["ram_count"] += 1
                gpu = _to_float(sample.get("gpu"))
                if gpu is not None:
                    bucket["gpu_sum"] += gpu
                    bucket["gpu_count"] += 1
                bucket["sample_count"] += 1

            # Append to 1-min buffer
            if statistics_id not in _stats_1m_buffer:
                _stats_1m_buffer[statistics_id] = []

            for bucket_start in sorted(minute_buckets.keys()):
                agg = minute_buckets[bucket_start]
                entry = {
                    "window_start": bucket_start.isoformat(),
                    "window_end": (bucket_start + timedelta(minutes=1)).isoformat(),
                    "avg_cpu": round(agg["cpu_sum"] / agg["cpu_count"], 2) if agg["cpu_count"] else None,
                    "avg_ram": round(agg["ram_sum"] / agg["ram_count"], 2) if agg["ram_count"] else None,
                    "avg_gpu": round(agg["gpu_sum"] / agg["gpu_count"], 2) if agg["gpu_count"] else None,
                    "samples": agg["sample_count"],
                    "cpu_points": agg["cpu_count"],
                    "ram_points": agg["ram_count"],
                    "gpu_points": agg["gpu_count"],
                    "calculated_at": run_stamp,
                }
                _stats_1m_buffer[statistics_id].append(entry)
                tier1_total += 1

            # Update MongoDB: keep only recent samples
            statistics_collection.update_one(
                {"id": statistics_id},
                {"$set": {"data": remaining, "updated_at": run_stamp}},
            )

            # Also update Redis raw cache
            if _redis_enabled and _redis_client is not None:
                _redis_client.delete(_redis_key_stats_raw(statistics_id))
                if remaining:
                    encoded = [_redis_serialize(s) for s in remaining if isinstance(s, dict)]
                    if encoded:
                        _redis_client.rpush(_redis_key_stats_raw(statistics_id), *encoded)
                _redis_client.set(_redis_key_stats_updated(statistics_id), run_stamp)
                _redis_client.sadd(_redis_stats_ids_key, statistics_id)

        # ══════════════════════════════════════════════════════════════
        # TIER 2: 1-min averages → 5-min averages
        # Move 1-min entries whose window_end is older than 5 minutes
        # ══════════════════════════════════════════════════════════════
        for statistics_id in list(_stats_1m_buffer.keys()):
            entries = _stats_1m_buffer.get(statistics_id, [])
            old_entries = []
            new_entries = []

            for entry in entries:
                we_dt = _parse_sample_time(entry.get("window_end"))
                if we_dt and we_dt < m1_cutoff:
                    old_entries.append(entry)
                else:
                    new_entries.append(entry)

            _stats_1m_buffer[statistics_id] = new_entries

            if not old_entries:
                continue

            # Group by 5-minute window
            five_min_buckets = {}
            for entry in old_entries:
                ws_dt = _parse_sample_time(entry.get("window_start"))
                if not ws_dt:
                    continue
                bucket_start = _bucket_5m(ws_dt)
                bucket = five_min_buckets.setdefault(bucket_start, {
                    "cpu_sum": 0.0, "cpu_count": 0,
                    "ram_sum": 0.0, "ram_count": 0,
                    "gpu_sum": 0.0, "gpu_count": 0,
                    "total_samples": 0,
                })
                if entry.get("avg_cpu") is not None:
                    cp = entry.get("cpu_points", 1) or 1
                    bucket["cpu_sum"] += entry["avg_cpu"] * cp
                    bucket["cpu_count"] += cp
                if entry.get("avg_ram") is not None:
                    rp = entry.get("ram_points", 1) or 1
                    bucket["ram_sum"] += entry["avg_ram"] * rp
                    bucket["ram_count"] += rp
                if entry.get("avg_gpu") is not None:
                    gp = entry.get("gpu_points", 1) or 1
                    bucket["gpu_sum"] += entry["avg_gpu"] * gp
                    bucket["gpu_count"] += gp
                bucket["total_samples"] += entry.get("samples", 0)

            if statistics_id not in _stats_5m_buffer:
                _stats_5m_buffer[statistics_id] = []

            for bucket_start in sorted(five_min_buckets.keys()):
                agg = five_min_buckets[bucket_start]
                fentry = {
                    "window_start": bucket_start.isoformat(),
                    "window_end": (bucket_start + timedelta(minutes=5)).isoformat(),
                    "avg_cpu": round(agg["cpu_sum"] / agg["cpu_count"], 2) if agg["cpu_count"] else None,
                    "avg_ram": round(agg["ram_sum"] / agg["ram_count"], 2) if agg["ram_count"] else None,
                    "avg_gpu": round(agg["gpu_sum"] / agg["gpu_count"], 2) if agg["gpu_count"] else None,
                    "samples": agg["total_samples"],
                    "cpu_points": agg["cpu_count"],
                    "ram_points": agg["ram_count"],
                    "gpu_points": agg["gpu_count"],
                    "calculated_at": run_stamp,
                }
                _stats_5m_buffer[statistics_id].append(fentry)
                tier2_total += 1

        # ══════════════════════════════════════════════════════════════
        # TIER 3: 5-min averages → 15-min averages → statistic_hours
        # Move 5-min entries whose window_end is older than 15 minutes
        # ══════════════════════════════════════════════════════════════
        for statistics_id in list(_stats_5m_buffer.keys()):
            entries = _stats_5m_buffer.get(statistics_id, [])
            old_entries = []
            new_entries = []

            for entry in entries:
                we_dt = _parse_sample_time(entry.get("window_end"))
                if we_dt and we_dt < m5_cutoff:
                    old_entries.append(entry)
                else:
                    new_entries.append(entry)

            _stats_5m_buffer[statistics_id] = new_entries

            if not old_entries:
                continue

            # Group by 15-minute window
            fifteen_min_buckets = {}
            for entry in old_entries:
                ws_dt = _parse_sample_time(entry.get("window_start"))
                if not ws_dt:
                    continue
                bucket_start = _bucket_15m(ws_dt)
                bucket = fifteen_min_buckets.setdefault(bucket_start, {
                    "cpu_sum": 0.0, "cpu_count": 0,
                    "ram_sum": 0.0, "ram_count": 0,
                    "gpu_sum": 0.0, "gpu_count": 0,
                    "total_samples": 0,
                })
                if entry.get("avg_cpu") is not None:
                    cp = entry.get("cpu_points", 1) or 1
                    bucket["cpu_sum"] += entry["avg_cpu"] * cp
                    bucket["cpu_count"] += cp
                if entry.get("avg_ram") is not None:
                    rp = entry.get("ram_points", 1) or 1
                    bucket["ram_sum"] += entry["avg_ram"] * rp
                    bucket["ram_count"] += rp
                if entry.get("avg_gpu") is not None:
                    gp = entry.get("gpu_points", 1) or 1
                    bucket["gpu_sum"] += entry["avg_gpu"] * gp
                    bucket["gpu_count"] += gp
                bucket["total_samples"] += entry.get("samples", 0)

            new_hours_rows = []
            for bucket_start in sorted(fifteen_min_buckets.keys()):
                agg = fifteen_min_buckets[bucket_start]
                row = {
                    "window_start": bucket_start.isoformat(),
                    "window_end": (bucket_start + timedelta(minutes=15)).isoformat(),
                    "avg_cpu": round(agg["cpu_sum"] / agg["cpu_count"], 2) if agg["cpu_count"] else None,
                    "avg_ram": round(agg["ram_sum"] / agg["ram_count"], 2) if agg["ram_count"] else None,
                    "avg_gpu": round(agg["gpu_sum"] / agg["gpu_count"], 2) if agg["gpu_count"] else None,
                    "samples": agg["total_samples"],
                    "cpu_points": agg["cpu_count"],
                    "ram_points": agg["ram_count"],
                    "gpu_points": agg["gpu_count"],
                    "calculated_at": run_stamp,
                }
                new_hours_rows.append(row)
                tier3_total += 1

            # Merge into statistic_hours MongoDB collection
            _merge_into_statistic_hours(statistics_id, new_hours_rows, run_stamp)

            print(
                f"📊 Tiered rollup [{statistics_id}] "
                f"15m-windows={len(new_hours_rows)} "
                f"samples={sum(r.get('samples', 0) for r in new_hours_rows)}"
            )

        return tier1_total, tier2_total, tier3_total

    try:
        t1, t2, t3 = await loop.run_in_executor(None, _worker)
        if t1 > 0 or t2 > 0 or t3 > 0:
            print(
                f"✓ Tiered rollup done: "
                f"raw→1m={t1}, 1m→5m={t2}, 5m→15m→hours={t3}"
            )
    except Exception as e:
        print(f"✗ Tiered rollup error: {e}")


async def rollup_statistics_scheduler():
    """Run tiered rollup every N seconds (replaces old 10-min flat rollup)."""
    # Run once on startup to flush any already-closed windows.
    await _tiered_rollup()

    while True:
        try:
            await asyncio.sleep(_TIERED_ROLLUP_INTERVAL_SEC)
            await _tiered_rollup()
        except Exception as e:
            print(f"✗ Tiered rollup scheduler error: {e}")
            await asyncio.sleep(10)

@app.post("/delete")
async def delete_data(payload: dict):
    """Xóa dữ liệu theo name (machine name)"""
    try:
        name = payload.get('name', '')
        ip = payload.get('ip', '')
        
        # Xóa theo name (machine name) để đảm bảo chính xác
        query = {"name": name} if name else {"ip": ip}
        
        result = collection.delete_one(query)
        
        # Also remove from in-memory cache
        if name and name in _data_cache:
            del _data_cache[name]
        
        if result.deleted_count > 0:
            print(f"✓ Deleted: {name} ({ip})")
            # Broadcast update to all WebSocket clients
            await broadcast_updates()
            return JSONResponse(content={
                "success": True, 
                "deleted": result.deleted_count,
                "message": f"Deleted {name} ({ip})"
            })
        else:
            print(f"⚠ Not found: {name} ({ip})")
            return JSONResponse(content={
                "success": False,
                "deleted": 0,
                "message": f"Not found: {name} ({ip})"
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
            srt_list = _normalize_payload_list(doc.get("SRT", []))
            stream_list = _normalize_payload_list(doc.get("stream", []))
            entry = {
                "timestamp": doc.get("last_updated", doc.get("timestamp", "")),
                "data": {
                    "name": doc.get("name", ""),
                    "name_edit": doc.get("name_edit", ""),
                    "ip": doc.get("ip", ""),
                    "ipwan": doc.get("ipwan", ""),
                    "statusapp": doc.get("statusapp", 0),
                    "ping": doc.get("ping"),
                    "ping_timeouts": doc.get("ping_timeouts", 0),
                    "cpu": doc.get("temperature", doc.get("cpu")),
                    "memory": doc.get("memory", doc.get("ram")),
                    "gpu": doc.get("gpu"),
                    "sender_mbps": doc.get("sender_mbps"),
                    "receiver_mbps": doc.get("receiver_mbps"),
                    "vmixsend": doc.get("vmixsend"),
                    "vmixreceive": doc.get("vmixreceive"),
                    "PIDVMIX": doc.get("PIDVMIX", ""),
                    "vmix_recording": doc.get("vmix_recording", False),
                    "vmix_streaming": doc.get("vmix_streaming", False),
                    "vmix_external": doc.get("vmix_external", False),
                    "vmix_multicorder": doc.get("vmix_multicorder", False),
                    "MultirecordingStatus": doc.get("MultirecordingStatus", False),
                    "List_REcord": doc.get("List_REcord", []),
                    "ListMultiREcord": doc.get("ListMultiREcord", doc.get("ListMultiRecord", [])),
                    "resolution": doc.get("resolution", "—"),
                    "SRT": srt_list,
                    "stream": stream_list,
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
        port = payload.get('port', None)
        query = {"ip": ip}
        if port is not None:
            query["port"] = port
        result = collection.update_many(
            query,
            {"$set": {"name": new_name}}
        )
        print(f"✓ Updated {result.modified_count} documents: {old_name} → {new_name} (ip={ip}, port={port})")
        await broadcast_updates()
        return JSONResponse(content={"success": True, "modified": result.modified_count})
    except Exception as e:
        print(f"✗ Update error: {e}")
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)

@app.post("/update_name_edit")
async def update_name_edit(payload: dict):
    """Update name_edit field for a machine in MongoDB and in-memory cache"""
    try:
        name = payload.get('name', '')
        ip = payload.get('ip', '')
        name_edit = payload.get('name_edit', '')
        
        query = {}
        if name:
            query["name"] = name
        elif ip:
            query["ip"] = ip
        else:
            return JSONResponse(content={"success": False, "error": "Missing 'name' or 'ip' field"}, status_code=400)
            
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: collection.update_many(
                query,
                {"$set": {"name_edit": name_edit}}
            )
        )
        
        # Update in-memory cache
        updated_cache_count = 0
        if name:
            if name in _data_cache:
                _data_cache[name]["name_edit"] = name_edit
                updated_cache_count += 1
        elif ip:
            for k, v in _data_cache.items():
                if v.get("ip") == ip:
                    v["name_edit"] = name_edit
                    updated_cache_count += 1
                    
        print(f"✓ Updated name_edit to '{name_edit}' for query {query} (modified db: {result.modified_count}, cache: {updated_cache_count})")
        
        # Broadcast update to all WebSocket clients
        await broadcast_updates()
        
        return JSONResponse(content={
            "success": True,
            "modified_db": result.modified_count,
            "modified_cache": updated_cache_count,
            "message": f"Updated name_edit to '{name_edit}' successfully"
        })
    except Exception as e:
        print(f"✗ Update name_edit error: {e}")
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

@app.get("/accounts")
async def list_accounts():
    """Lấy danh sách tài khoản web (không trả password hash)."""
    try:
        docs = list(
            accounts_collection.find(
                {},
                {"_id": 0, "username": 1, "password": 1, "created_at": 1, "email": 1, "phone": 1, "is_locked": 1, "role": 1, "allowed_channels": 1}
            ).sort("username", 1)
        )
        # Normalize returned documents
        processed_docs = []
        for doc in docs:
            processed_docs.append({
                "username": doc.get("username", ""),
                "password": doc.get("password", ""),
                "created_at": doc.get("created_at", ""),
                "email": doc.get("email", ""),
                "phone": doc.get("phone", ""),
                "is_locked": bool(doc.get("is_locked", False)),
                "role": doc.get("role", ""),
                "allowed_channels": doc.get("allowed_channels", [])
            })
        return JSONResponse(content=processed_docs)
    except Exception as e:
        print(f"✗ List accounts error: {e}")
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@app.post("/login")
async def login_account(payload: dict):
    """Xác thực đăng nhập tài khoản web."""
    try:
        username = str(payload.get("username", "")).strip()
        password = str(payload.get("password", ""))

        if not username or not password:
            return JSONResponse(
                content={"success": False, "message": "username and password are required"},
                status_code=400,
            )

        doc = accounts_collection.find_one(
            {"username_key": username.lower()},
            {"_id": 0, "username": 1, "password": 1, "password_hash": 1, "is_locked": 1, "role": 1, "allowed_channels": 1},
        )
        if not doc:
            return JSONResponse(content={"success": False, "message": "invalid credentials"}, status_code=401)

        # Check if locked
        if doc.get("is_locked", False):
            return JSONResponse(content={"success": False, "message": "Tài khoản đã bị khóa"}, status_code=403)

        provided_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
        stored_plain = str(doc.get("password", ""))
        stored_hash = str(doc.get("password_hash", ""))

        valid = hmac.compare_digest(stored_plain, password) or hmac.compare_digest(stored_hash, provided_hash)
        if not valid:
            return JSONResponse(content={"success": False, "message": "invalid credentials"}, status_code=401)

        # Retrieve permissions based on user's role
        role_name = doc.get("role", "")
        permissions = []
        if role_name:
            if role_name == "admin":
                permissions = ["Tổng quan", "SRT", "Thông số Stream", "URL & Key", "FFmpeg", "Thống kê", "Vmix Monitor", "Record & MultiCorder", "ViewSync", "Speedtest", "Debug Log", "Tài khoản", "Phân quyền"]
            else:
                role_doc = roles_collection.find_one({"role_key": role_name.lower()})
                if role_doc:
                    permissions = role_doc.get("permissions", [])

        return JSONResponse(content={
            "success": True, 
            "username": doc.get("username", username),
            "role": role_name,
            "permissions": permissions,
            "allowed_channels": doc.get("allowed_channels", [])
        })
    except Exception as e:
        print(f"✗ Login account error: {e}")
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)

@app.get("/user_profile/{username}")
async def get_user_profile(username: str):
    """Lấy thông tin profile, vai trò, quyền và allowed_channels của user."""
    try:
        doc = accounts_collection.find_one(
            {"username_key": username.lower()},
            {"_id": 0, "username": 1, "is_locked": 1, "role": 1, "allowed_channels": 1},
        )
        if not doc:
            return JSONResponse(content={"success": False, "message": "Không tìm thấy người dùng"}, status_code=404)
        if doc.get("is_locked", False):
            return JSONResponse(content={"success": False, "message": "Tài khoản đã bị khóa"}, status_code=403)

        role_name = doc.get("role", "")
        permissions = []
        if role_name:
            if role_name == "admin":
                permissions = ["Tổng quan", "SRT", "Thông số Stream", "URL & Key", "FFmpeg", "Thống kê", "Vmix Monitor", "ViewSync", "Speedtest", "Debug Log", "Tài khoản", "Phân quyền"]
            else:
                role_doc = roles_collection.find_one({"role_key": role_name.lower()})
                if role_doc:
                    permissions = role_doc.get("permissions", [])

        return JSONResponse(content={
            "success": True,
            "username": doc.get("username", username),
            "role": role_name,
            "permissions": permissions,
            "allowed_channels": doc.get("allowed_channels", [])
        })
    except Exception as e:
        print(f"✗ Get user profile error: {e}")
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)

@app.post("/create_account")
async def create_account(payload: dict):
    """Tạo tài khoản web mới."""
    try:
        username = str(payload.get("username", "")).strip()
        password = str(payload.get("password", "")).strip()
        email = str(payload.get("email", "")).strip()
        phone = str(payload.get("phone", "")).strip()
        role = str(payload.get("role", "")).strip()
        allowed_channels = payload.get("allowed_channels", [])
        if not isinstance(allowed_channels, list):
            allowed_channels = []

        if not username:
            return JSONResponse(content={"success": False, "message": "username is required"}, status_code=400)
        if len(password) < 4:
            return JSONResponse(content={"success": False, "message": "password must be at least 4 characters"}, status_code=400)

        username_key = username.lower()
        password_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
        created_at = datetime.now(VIETNAM_TZ).isoformat()

        existing = accounts_collection.find_one({"username_key": username_key})
        if existing:
            # Legacy record repair: old account may not contain plain password.
            if not existing.get("password"):
                accounts_collection.update_one(
                    {"_id": existing["_id"]},
                    {"$set": {
                        "password": password, 
                        "password_hash": password_hash,
                        "email": email,
                        "phone": phone,
                        "role": role,
                        "is_locked": False,
                        "allowed_channels": allowed_channels
                    }}
                )
                return JSONResponse(content={"success": True, "username": username, "updated": True}, status_code=200)
            return JSONResponse(content={"success": False, "message": "username already exists"}, status_code=409)

        try:
            accounts_collection.insert_one({
                "username": username,
                "username_key": username_key,
                "password": password,
                "password_hash": password_hash,
                "created_at": created_at,
                "email": email,
                "phone": phone,
                "role": role,
                "is_locked": False,
                "allowed_channels": allowed_channels
            })
        except Exception:
            return JSONResponse(content={"success": False, "message": "username already exists"}, status_code=409)

        return JSONResponse(content={"success": True, "username": username, "created_at": created_at}, status_code=201)
    except Exception as e:
        print(f"✗ Create account error: {e}")
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)

@app.post("/update_account")
async def update_account(payload: dict):
    """Cập nhật thông tin tài khoản web."""
    try:
        username = str(payload.get("username", "")).strip()
        if not username:
            return JSONResponse(content={"success": False, "message": "username is required"}, status_code=400)

        username_key = username.lower()
        existing = accounts_collection.find_one({"username_key": username_key})
        if not existing:
            return JSONResponse(content={"success": False, "message": "account not found"}, status_code=404)

        # Master admin account protection checks
        if username_key == "admin":
            if payload.get("is_locked") is True:
                return JSONResponse(content={"success": False, "message": "Không thể khóa tài khoản master admin"}, status_code=400)
            if "role" in payload and str(payload.get("role")).strip() != "admin":
                return JSONResponse(content={"success": False, "message": "Không thể thay đổi vai trò tài khoản master admin"}, status_code=400)

        update_fields = {}
        
        # Check if password is to be updated
        if "password" in payload:
            password = str(payload.get("password", "")).strip()
            if password:  # Only change if not empty
                if len(password) < 4:
                    return JSONResponse(content={"success": False, "message": "password must be at least 4 characters"}, status_code=400)
                update_fields["password"] = password
                update_fields["password_hash"] = hashlib.sha256(password.encode("utf-8")).hexdigest()

        if "email" in payload:
            update_fields["email"] = str(payload.get("email", "")).strip()

        if "phone" in payload:
            update_fields["phone"] = str(payload.get("phone", "")).strip()

        if "role" in payload:
            update_fields["role"] = str(payload.get("role", "")).strip()

        if "is_locked" in payload:
            update_fields["is_locked"] = bool(payload.get("is_locked", False))

        if "allowed_channels" in payload:
            allowed_channels = payload.get("allowed_channels", [])
            if isinstance(allowed_channels, list):
                update_fields["allowed_channels"] = allowed_channels

        if update_fields:
            accounts_collection.update_one({"username_key": username_key}, {"$set": update_fields})

        return JSONResponse(content={"success": True, "username": username})
    except Exception as e:
        print(f"✗ Update account error: {e}")
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)

@app.post("/delete_account")
async def delete_account(payload: dict):
    """Xóa tài khoản web theo username."""
    try:
        username = str(payload.get("username", "")).strip()
        if not username:
            return JSONResponse(content={"success": False, "message": "username is required"}, status_code=400)

        # Master admin account protection checks
        if username.lower() == "admin":
            return JSONResponse(content={"success": False, "message": "Không thể xóa tài khoản master admin"}, status_code=400)

        result = accounts_collection.delete_one({"username_key": username.lower()})
        if result.deleted_count > 0:
            return JSONResponse(content={"success": True, "deleted": 1, "username": username})
        return JSONResponse(content={"success": False, "deleted": 0, "message": "account not found"}, status_code=404)
    except Exception as e:
        print(f"✗ Delete account error: {e}")
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@app.get("/roles")
async def list_roles():
    """Lấy danh sách vai trò web."""
    try:
        docs = list(
            roles_collection.find(
                {},
                {"_id": 0, "role_key": 1, "name": 1, "description": 1, "permissions": 1, "created_at": 1}
            ).sort("role_key", 1)
        )
        return JSONResponse(content=docs)
    except Exception as e:
        print(f"✗ List roles error: {e}")
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@app.post("/create_role")
async def create_role(payload: dict):
    """Tạo vai trò web mới."""
    try:
        role_key = str(payload.get("role_key", "")).strip().lower()
        name = str(payload.get("name", "")).strip()
        description = str(payload.get("description", "")).strip()
        permissions = payload.get("permissions", [])

        if not role_key:
            return JSONResponse(content={"success": False, "message": "role_key is required"}, status_code=400)
        if not name:
            return JSONResponse(content={"success": False, "message": "name is required"}, status_code=400)

        existing = roles_collection.find_one({"role_key": role_key})
        if existing:
            return JSONResponse(content={"success": False, "message": "role_key already exists"}, status_code=409)

        created_at = datetime.now(VIETNAM_TZ).isoformat()
        roles_collection.insert_one({
            "role_key": role_key,
            "name": name,
            "description": description,
            "permissions": permissions,
            "created_at": created_at
        })
        return JSONResponse(content={"success": True, "role_key": role_key, "created_at": created_at}, status_code=201)
    except Exception as e:
        print(f"✗ Create role error: {e}")
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@app.post("/update_role")
async def update_role(payload: dict):
    """Cập nhật thông tin vai trò web."""
    try:
        role_key = str(payload.get("role_key", "")).strip().lower()
        if not role_key:
            return JSONResponse(content={"success": False, "message": "role_key is required"}, status_code=400)

        existing = roles_collection.find_one({"role_key": role_key})
        if not existing:
            return JSONResponse(content={"success": False, "message": "role not found"}, status_code=404)

        if role_key == "admin":
            return JSONResponse(content={"success": False, "message": "Không thể chỉnh sửa vai trò default admin"}, status_code=400)

        update_fields = {}
        if "name" in payload:
            update_fields["name"] = str(payload.get("name", "")).strip()
        if "description" in payload:
            update_fields["description"] = str(payload.get("description", "")).strip()
        if "permissions" in payload:
            update_fields["permissions"] = payload.get("permissions", [])

        if update_fields:
            roles_collection.update_one({"role_key": role_key}, {"$set": update_fields})

        return JSONResponse(content={"success": True, "role_key": role_key})
    except Exception as e:
        print(f"✗ Update role error: {e}")
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@app.post("/delete_role")
async def delete_role(payload: dict):
    """Xóa vai trò web."""
    try:
        role_key = str(payload.get("role_key", "")).strip().lower()
        if not role_key:
            return JSONResponse(content={"success": False, "message": "role_key is required"}, status_code=400)

        if role_key == "admin":
            return JSONResponse(content={"success": False, "message": "Không thể xóa vai trò default admin"}, status_code=400)

        # Kiểm tra xem có tài khoản nào đang gán vai trò này không
        account_using = accounts_collection.find_one({"role": role_key})
        if account_using:
            return JSONResponse(
                content={"success": False, "message": f"Không thể xóa vai trò này vì đang có tài khoản sử dụng ({account_using.get('username')})"},
                status_code=400
            )

        result = roles_collection.delete_one({"role_key": role_key})
        if result.deleted_count > 0:
            return JSONResponse(content={"success": True, "deleted": 1, "role_key": role_key})
        return JSONResponse(content={"success": False, "deleted": 0, "message": "role not found"}, status_code=404)
    except Exception as e:
        print(f"✗ Delete role error: {e}")
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@app.get("/speedtest")
async def run_speedtest():
    """Run speedtest-cli and return parsed JSON results."""
    try:
        raw_cmd = os.getenv("SPEEDTEST_CLI_CMD", "speedtest-cli").strip() or "speedtest-cli"
        base_cmd = raw_cmd.split()
        if not base_cmd:
            return JSONResponse(content={"success": False, "message": "speedtest-cli command not configured"}, status_code=500)

        if shutil.which(base_cmd[0]) is None:
            return JSONResponse(
                content={"success": False, "message": "speedtest-cli is not installed"},
                status_code=503,
            )

        full_cmd = [*base_cmd, "--json"]
        result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=90)
        if result.returncode != 0:
            return JSONResponse(
                content={"success": False, "message": result.stderr.strip() or "speedtest-cli failed"},
                status_code=500,
            )

        try:
            payload = json.loads(result.stdout)
        except Exception:
            return JSONResponse(
                content={"success": False, "message": "invalid speedtest-cli output"},
                status_code=500,
            )

        download_bps = payload.get("download")
        upload_bps = payload.get("upload")
        ping_ms = payload.get("ping")
        client_meta = payload.get("client") if isinstance(payload.get("client"), dict) else {}
        ipwan = client_meta.get("ip")
        isp_name = client_meta.get("isp") or client_meta.get("isp_name") or client_meta.get("ispName")
        result_payload = {
            "success": True,
            "timestamp": payload.get("timestamp"),
            "ping_ms": ping_ms,
            "download_bps": download_bps,
            "upload_bps": upload_bps,
            "download_mbps": (download_bps / 1_000_000) if isinstance(download_bps, (int, float)) else None,
            "upload_mbps": (upload_bps / 1_000_000) if isinstance(upload_bps, (int, float)) else None,
            "ipwan": ipwan,
            "isp": isp_name,
            "server": payload.get("server", {}),
            "raw": payload,
        }
        return JSONResponse(content=result_payload)
    except subprocess.TimeoutExpired:
        return JSONResponse(
            content={"success": False, "message": "speedtest-cli timeout"},
            status_code=504,
        )
    except Exception as e:
        print(f"✗ Speedtest error: {e}")
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)

@app.get("/statistics/{statistics_id}")
async def get_statistics(statistics_id: str, limit: int = _stats_default_limit):
    """Get CPU/RAM history by statistics id."""
    try:
        safe_limit = max(1, min(limit, _stats_response_max_limit))

        ts_doc = await _mongo_get_statistics_ts(statistics_id, safe_limit)
        if ts_doc and ts_doc.get("data"):
            return JSONResponse(content=ts_doc)

        doc = await _redis_get_statistics_doc(statistics_id)
        if not doc:
            loop = asyncio.get_event_loop()
            doc = await loop.run_in_executor(
                None,
                lambda: statistics_collection.find_one(
                    {"id": statistics_id},
                    {"_id": 0, "id": 1, "data": 1, "updated_at": 1}
                )
            )
            if doc:
                await _redis_set_statistics_doc(statistics_id, doc.get("data", []), doc.get("updated_at", ""))

        if not doc or not doc.get("data"):
            cached = list(_realtime_stats_cache.get(statistics_id, []))
            if cached:
                return JSONResponse(content={
                    "id": statistics_id,
                    "data": cached[-safe_limit:],
                    "updated_at": _realtime_stats_updated.get(statistics_id, cached[-1].get("time", "")),
                })

        if not doc:
            return JSONResponse(content={"id": statistics_id, "data": [], "updated_at": ""})

        samples = doc.get("data", [])
        updated_at = str(doc.get("updated_at", "") or "")

        # Production-safe fallback:
        # If statistics data is stale/empty while /logs is still updating,
        # synthesize latest point from logs so charts keep moving.
        last_sample_time = samples[-1].get("time", "") if samples else ""
        last_sample_dt = _parse_sample_time(last_sample_time) if last_sample_time else None
        now_vn = datetime.now(VIETNAM_TZ)
        stale_threshold = timedelta(seconds=30)
        is_stale = (last_sample_dt is None) or ((now_vn - last_sample_dt) > stale_threshold)

        if not samples or is_stale:
            ip_text, port_text, port_int = _parse_statistics_id(statistics_id)
            latest_doc = None
            if ip_text and port_text:
                loop = asyncio.get_event_loop()

                def _load_latest_from_logs():
                    port_candidates = [port_text]
                    if port_int is not None:
                        port_candidates.append(str(port_int))
                    return collection.find_one(
                        {"ip": ip_text, "SRT.port": {"$in": port_candidates}},
                        {
                            "_id": 0,
                            "temperature": 1,
                            "memory": 1,
                            "gpu": 1,
                            "cpu": 1,
                            "ram": 1,
                            "last_updated": 1,
                        },
                    )

                latest_doc = await loop.run_in_executor(None, _load_latest_from_logs)

            if latest_doc:
                latest_time = str(latest_doc.get("last_updated", "") or "")
                latest_cpu = latest_doc.get("temperature", latest_doc.get("cpu"))
                latest_ram = latest_doc.get("memory", latest_doc.get("ram"))
                latest_gpu = latest_doc.get("gpu")
                latest_sample = {
                    "cpu": latest_cpu,
                    "ram": latest_ram,
                    "gpu": latest_gpu,
                    "time": latest_time,
                }

                if latest_time and last_sample_time != latest_time:
                    samples = (samples + [latest_sample])[-safe_limit:]
                    updated_at = latest_time

        doc["data"] = samples[-safe_limit:]
        doc["updated_at"] = updated_at
        return JSONResponse(content=doc)
    except Exception as e:
        print(f"✗ Get statistics error: {e}")
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)

@app.get("/statistic_hours")
async def get_all_statistic_hours():
    """Get all machines' hourly (10-min rollup) statistics."""
    try:
        docs = await _redis_get_all_stat_hours_docs()
        if docs is None or len(docs) == 0:
            loop = asyncio.get_event_loop()
            docs = await loop.run_in_executor(
                None,
                lambda: list(statistics_hours_collection.find(
                    {},
                    {"_id": 0, "id": 1, "data": 1, "updated_at": 1}
                ))
            )
            for doc in docs:
                stat_id = doc.get("id")
                if stat_id:
                    await _redis_set_stat_hours_doc(stat_id, doc)
        return JSONResponse(content=docs)
    except Exception as e:
        print(f"✗ Get all statistic_hours error: {e}")
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)

@app.get("/statistic_hours/{statistics_id:path}")
async def get_statistic_hours(statistics_id: str):
    """Get hourly (10-min rollup) statistics for a specific machine."""
    try:
        doc = await _redis_get_stat_hours_doc(statistics_id)
        if not doc:
            loop = asyncio.get_event_loop()
            doc = await loop.run_in_executor(
                None,
                lambda: statistics_hours_collection.find_one(
                    {"id": statistics_id},
                    {"_id": 0, "id": 1, "data": 1, "updated_at": 1}
                )
            )
            if doc:
                await _redis_set_stat_hours_doc(statistics_id, doc)
        if not doc:
            return JSONResponse(content={"id": statistics_id, "data": [], "updated_at": ""})
        return JSONResponse(content=doc)
    except Exception as e:
        print(f"✗ Get statistic_hours error: {e}")
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

@app.post("/save_game_selected")
async def save_game_selected(payload: dict):
    """Lưu danh sách máy đã chọn cho một game vào cấu hình Game_Selected"""
    try:
        game = payload.get('game', '')
        machines = payload.get('machines', [])
        visible_status = payload.get('visible_status', 'ON')
        
        if not game:
            return JSONResponse(content={"success": False, "error": "Missing 'game' field"}, status_code=400)
            
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: game_selected_collection.update_one(
                {"game": game},
                {"$set": {"machines": machines, "visible_status": visible_status}},
                upsert=True
            )
        )
        
        print(f"✓ Saved {len(machines)} machines for game '{game}' (visible_status={visible_status}) in Game_Selected")
        return JSONResponse(content={
            "success": True, 
            "message": f"Saved {len(machines)} machines for {game} successfully"
        })
    except Exception as e:
        print(f"✗ Save game selected error: {e}")
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)

@app.get("/load_game_selected")
async def load_game_selected():
    """Load danh sách Game_Selected từ database"""
    try:
        loop = asyncio.get_event_loop()
        documents = await loop.run_in_executor(
            None,
            lambda: list(game_selected_collection.find())
        )
        
        entries = []
        for doc in documents:
            doc.pop('_id', None)
            if 'visible_status' not in doc:
                doc['visible_status'] = 'ON'
            if 'hidden_machines' not in doc:
                doc['hidden_machines'] = []
            entries.append(doc)
            
        print(f"✓ Loaded {len(entries)} game assignments from Game_Selected")
        return JSONResponse(content=entries)
    except Exception as e:
        print(f"✗ Load game selected error: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/delete_game_selected")
async def delete_game_selected(payload: dict):
    """Xóa cấu hình game khỏi Game_Selected"""
    try:
        game = payload.get('game', '')
        if not game:
            return JSONResponse(content={"success": False, "error": "Missing 'game' field"}, status_code=400)
            
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: game_selected_collection.delete_one({"game": game})
        )
        
        if result.deleted_count == 0:
            return JSONResponse(content={"success": False, "error": "Không tìm thấy cấu hình kênh để xóa"}, status_code=404)
            
        print(f"✓ Deleted game assignment for '{game}' from Game_Selected")
        return JSONResponse(content={
            "success": True, 
            "message": f"Xóa kênh '{game}' thành công"
        })
    except Exception as e:
        print(f"✗ Delete game selected error: {e}")
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)

@app.post("/toggle_visible_status")
async def toggle_visible_status(payload: dict):
    """Toggle visible_status ON/OFF cho một kênh game"""
    try:
        game = payload.get('game', '')
        visible_status = payload.get('visible_status', 'ON')
        
        if not game:
            return JSONResponse(content={"success": False, "error": "Missing 'game' field"}, status_code=400)
        if visible_status not in ('ON', 'OFF'):
            return JSONResponse(content={"success": False, "error": "visible_status must be 'ON' or 'OFF'"}, status_code=400)
            
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: game_selected_collection.update_one(
                {"game": game},
                {"$set": {"visible_status": visible_status}}
            )
        )
        
        if result.matched_count == 0:
            return JSONResponse(content={"success": False, "error": "Không tìm thấy kênh"}, status_code=404)
            
        print(f"✓ Toggled visible_status to '{visible_status}' for game '{game}'")
        return JSONResponse(content={
            "success": True, 
            "message": f"Đã cập nhật trạng thái hiển thị cho '{game}' thành {visible_status}"
        })
    except Exception as e:
        print(f"✗ Toggle visible_status error: {e}")
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)

@app.post("/toggle_machine_visibility")
async def toggle_machine_visibility(payload: dict):
    """Toggle ẩn/hiện một máy trong kênh game"""
    try:
        game = payload.get('game', '')
        machine = payload.get('machine', '')
        hidden = payload.get('hidden', True)
        
        if not game or not machine:
            return JSONResponse(content={"success": False, "error": "Missing 'game' or 'machine' field"}, status_code=400)
        
        loop = asyncio.get_event_loop()
        if hidden:
            # Add machine to hidden_machines array
            result = await loop.run_in_executor(
                None,
                lambda: game_selected_collection.update_one(
                    {"game": game},
                    {"$addToSet": {"hidden_machines": machine}}
                )
            )
        else:
            # Remove machine from hidden_machines array
            result = await loop.run_in_executor(
                None,
                lambda: game_selected_collection.update_one(
                    {"game": game},
                    {"$pull": {"hidden_machines": machine}}
                )
            )
        
        if result.matched_count == 0:
            return JSONResponse(content={"success": False, "error": "Không tìm thấy kênh"}, status_code=404)
        
        action = 'ẩn' if hidden else 'hiện'
        print(f"✓ Machine '{machine}' đã {action} trong kênh '{game}'")
        return JSONResponse(content={
            "success": True,
            "message": f"Đã {action} máy '{machine}' trong kênh '{game}'"
        })
    except Exception as e:
        print(f"✗ Toggle machine visibility error: {e}")
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@app.post("/create_shared_web")
async def create_shared_web(payload: dict):
    """Tạo một cấu hình chia sẻ URL mới với UUID"""
    try:
        import uuid
        allowed_features = payload.get("allowed_features", [])
        allowed_machines = payload.get("allowed_machines", [])
        selected_game = payload.get("selected_game", "__all__")
        share_type = payload.get("share_type", "machines")
        
        new_uuid = str(uuid.uuid4())
        doc = {
            "uuid": new_uuid,
            "allowed_features": allowed_features,
            "allowed_machines": allowed_machines,
            "selected_game": selected_game,
            "share_type": share_type,
            "created_at": datetime.now(VIETNAM_TZ).isoformat()
        }
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: shared_web_configs_collection.insert_one(doc)
        )
        
        print(f"✓ Created shared web config with UUID: {new_uuid}")
        return JSONResponse(content={
            "success": True,
            "uuid": new_uuid,
            "message": "Tạo cấu hình chia sẻ thành công"
        })
    except Exception as e:
        print(f"✗ Create shared web config error: {e}")
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)

@app.get("/shared_web_config/{uuid_str}")
async def get_shared_web_config(uuid_str: str):
    """Lấy cấu hình chia sẻ theo UUID"""
    try:
        loop = asyncio.get_event_loop()
        doc = await loop.run_in_executor(
            None,
            lambda: shared_web_configs_collection.find_one({"uuid": uuid_str})
        )
        
        if not doc:
            return JSONResponse(content={"success": False, "message": "Không tìm thấy cấu hình hoặc liên kết đã hết hạn/bị thu hồi"}, status_code=404)
            
        doc.pop('_id', None)
        return JSONResponse(content={
            "success": True,
            "data": doc
        })
    except Exception as e:
        print(f"✗ Get shared web config error: {e}")
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)

@app.get("/list_shared_web")
async def list_shared_web():
    """Lấy danh sách toàn bộ liên kết chia sẻ đã tạo"""
    try:
        loop = asyncio.get_event_loop()
        documents = await loop.run_in_executor(
            None,
            lambda: list(shared_web_configs_collection.find().sort("created_at", -1))
        )
        
        entries = []
        for doc in documents:
            doc.pop('_id', None)
            entries.append(doc)
            
        return JSONResponse(content=entries)
    except Exception as e:
        print(f"✗ List shared web configs error: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.delete("/delete_shared_web/{uuid_str}")
async def delete_shared_web(uuid_str: str):
    """Xóa cấu hình chia sẻ theo UUID"""
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: shared_web_configs_collection.delete_one({"uuid": uuid_str})
        )
        
        if result.deleted_count == 0:
            return JSONResponse(content={"success": False, "message": "Không tìm thấy cấu hình để xóa"}, status_code=404)
            
        print(f"✓ Deleted shared web config: {uuid_str}")
        return JSONResponse(content={"success": True, "message": "Đã xóa liên kết chia sẻ"})
    except Exception as e:
        print(f"✗ Delete shared web config error: {e}")
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)

@app.post("/update_shared_web/{uuid_str}")
async def update_shared_web(uuid_str: str, payload: dict):
    """Cập nhật cấu hình chia sẻ theo UUID"""
    try:
        allowed_features = payload.get("allowed_features", [])
        allowed_machines = payload.get("allowed_machines", [])
        selected_game = payload.get("selected_game", "__all__")
        share_type = payload.get("share_type", "machines")
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: shared_web_configs_collection.update_one(
                {"uuid": uuid_str},
                {"$set": {
                    "allowed_features": allowed_features,
                    "allowed_machines": allowed_machines,
                    "selected_game": selected_game,
                    "share_type": share_type,
                    "updated_at": datetime.now(VIETNAM_TZ).isoformat()
                }}
            )
        )
        
        if result.matched_count == 0:
            return JSONResponse(content={"success": False, "message": "Không tìm thấy cấu hình để cập nhật"}, status_code=404)
            
        print(f"✓ Updated shared web config for UUID: {uuid_str}")
        return JSONResponse(content={
            "success": True,
            "message": "Cập nhật liên kết thành công"
        })
    except Exception as e:
        print(f"✗ Update shared web config error: {e}")
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
        await websocket.send_json(_to_json_safe(data))
        
        # Keep connection alive
        while True:
            await websocket.receive_text()
            
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
    data = _to_json_safe(get_all_logs())  # đọc từ cache, không có I/O
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
                        
                        # Set all active SRT streams to OFF and send Discord notifications
                        srt_list = _data_cache[name].get("SRT", [])
                        if isinstance(srt_list, list):
                            for srt_item in srt_list:
                                if isinstance(srt_item, dict) and srt_item.get("status") == "ON":
                                    srt_item["status"] = "OFF"
                                    try:
                                        await asyncio.to_thread(
                                            send_discord_notification,
                                            name,
                                            _data_cache[name].get("ipwan", ""),
                                            srt_item.get("nameSRT", ""),
                                            str(srt_item.get("port", "")),
                                            "OFF",
                                            srt_item.get("quality", ""),
                                            srt_item.get("type", ""),
                                            srt_item.get("hostname", "")
                                        )
                                    except Exception as ne:
                                        print(f"⚠ Failed to send Discord notify for offline SRT {name}: {ne}")

                        _zero_out_metrics_if_offline(_data_cache[name])
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


async def ipwan_bandwidth_monitor_task():
    """Background task: ghi tổng băng thông sender & receiver của các ipwan mỗi 3 phút."""
    print("✓ Background task started: WAN IP Bandwidth monitoring every 3 minutes")
    while True:
        try:
            await asyncio.sleep(180)  # Wait 3 minutes (180 seconds)
            
            now_vn = datetime.now(VIETNAM_TZ)
            today_str = now_vn.strftime("%d-%m-%Y")
            timestamp = now_vn.isoformat()
            
            # Find all unique ipwans currently active or present in _data_cache
            ipwans = set()
            for doc in _data_cache.values():
                if isinstance(doc, dict):
                    ipwan_val = doc.get("ipwan")
                    if ipwan_val:
                        ipwans.add(ipwan_val)
            
            for ipwan in ipwans:
                # Get total bandwidth of all active stations under this ipwan
                total_sender, total_receiver = _get_ipwan_totals(ipwan)
                
                # Fetch/initialize cached values
                cached = await _async_get_cached_ipwan_stats(ipwan, today_str)
                
                # Update max values in cache
                if total_sender > cached["sender_max"]:
                    cached["sender_max"] = total_sender
                if total_receiver > cached["receiver_max"]:
                    cached["receiver_max"] = total_receiver
                    
                # Update min values in cache (only for non-zero active bandwidth)
                if total_sender > 0.0 and (cached["sender_min"] == 0.0 or total_sender < cached["sender_min"]):
                    cached["sender_min"] = total_sender
                if total_receiver > 0.0 and (cached["receiver_min"] == 0.0 or total_receiver < cached["receiver_min"]):
                    cached["receiver_min"] = total_receiver
                
                # Write/Update the record in MongoDB and append to history
                await _mongo_upsert_ipwan_bandwidth(
                    ipwan=ipwan,
                    today_str=today_str,
                    sender=total_sender,
                    receiver=total_receiver,
                    sender_max=cached["sender_max"],
                    receiver_max=cached["receiver_max"],
                    sender_min=cached["sender_min"],
                    receiver_min=cached["receiver_min"],
                    timestamp=timestamp,
                    push_history=True
                )
                
        except Exception as e:
            print(f"✗ Error in ipwan_bandwidth_monitor_task: {e}")



async def flush_statistics_from_cache():
    """Persist one statistics sample per machine every N seconds from in-memory cache."""
    while True:
        try:
            await asyncio.sleep(_stats_flush_interval_sec)
            now_vn = datetime.now(VIETNAM_TZ)
            timestamp = now_vn.isoformat()
            cutoff = now_vn - timedelta(seconds=_stats_flush_max_age_sec)

            for machine_name, doc in list(_data_cache.items()):
                if not isinstance(doc, dict):
                    continue

                last_updated_str = str(doc.get("last_updated", "") or "")
                if not last_updated_str:
                    continue

                try:
                    last_updated = datetime.fromisoformat(last_updated_str)
                    if last_updated.tzinfo is None:
                        last_updated = VIETNAM_TZ.localize(last_updated)
                    last_updated = last_updated.astimezone(VIETNAM_TZ)
                except Exception:
                    continue

                # Skip stale machines to avoid writing old values forever.
                if last_updated < cutoff:
                    continue

                srt_doc = doc.get("SRT", {})
                if not isinstance(srt_doc, dict):
                    srt_doc = {}
                statistics_id = _build_statistics_id(doc.get("ip"), srt_doc.get("port", ""), machine_name)
                cpu_value = doc.get("temperature", doc.get("cpu"))
                ram_value = doc.get("memory", doc.get("ram"))
                gpu_value = doc.get("gpu")

                sample = {
                    "cpu": cpu_value,
                    "ram": ram_value,
                    "gpu": gpu_value,
                    "time": timestamp,
                }

                bucket = _realtime_stats_cache.get(statistics_id)
                if bucket is None:
                    bucket = deque(maxlen=_realtime_stats_max_points)
                    _realtime_stats_cache[statistics_id] = bucket
                bucket.append(sample)
                _realtime_stats_updated[statistics_id] = timestamp

                asyncio.create_task(_mongo_append_statistics(statistics_id, cpu_value, ram_value, gpu_value, timestamp))
                asyncio.create_task(_mongo_insert_statistics_ts(statistics_id, cpu_value, ram_value, gpu_value, timestamp))
                asyncio.create_task(_redis_append_statistics_sample(statistics_id, sample, timestamp))
        except Exception as e:
            print(f"✗ Error in flush_statistics_from_cache: {e}")

async def _daily_cleanup_task():
    """Xóa sạch dữ liệu thống kê vào 3:00 sáng mỗi ngày"""
    global _realtime_stats_cache, _stats_1m_buffer, _stats_5m_buffer, _realtime_stats_updated
    last_cleaned_date = None
    
    while True:
        try:
            now = datetime.now()
            # Kiểm tra xem có đúng 3:00 sáng không
            if now.hour == 3 and now.minute == 0 and last_cleaned_date != now.date():
                print(f"🧹 [CLEANUP] Bắt đầu dọn dẹp dữ liệu định kỳ (3:00 AM {now.date()})...")
                
                # 1. Xóa trong MongoDB
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, lambda: statistics_collection.delete_many({}))
                await loop.run_in_executor(None, lambda: statistics_hours_collection.delete_many({}))
                await loop.run_in_executor(None, lambda: statistics_ts_collection.delete_many({}))
                await loop.run_in_executor(None, lambda: debug_logs_collection.delete_many({}))
                
                # 2. Xóa trong Redis (nếu có)
                if _redis_enabled and _redis_client is not None:
                    try:
                        keys_to_del = _redis_client.keys("v_stat_hours:*") + _redis_client.keys("v_stats:*")
                        if keys_to_del:
                            _redis_client.delete(*keys_to_del)
                    except Exception:
                        pass
                
                # 3. Reset buffers trong Python
                _realtime_stats_cache.clear()
                _stats_1m_buffer.clear()
                _stats_5m_buffer.clear()
                _realtime_stats_updated.clear()
                
                last_cleaned_date = now.date()
                print("✓ [CLEANUP] Đã xóa sạch statistic, statistic_hours và statistics_ts.")
            
            await asyncio.sleep(30) # Check mỗi 30 giây
        except Exception as e:
            print(f"✗ Daily cleanup error: {e}")
            await asyncio.sleep(60)

async def debug_logs_monitoring_task():
    """Ghi toàn bộ thông số thiết bị từ cache vào collection debug_logs mỗi 3 giây và tự động xóa log cũ > 7 tiếng"""
    print("✓ Background task started: Debug Logs collection writer every 3 seconds")
    while True:
        try:
            await asyncio.sleep(3)
            current_logs = list(_data_cache.values())
            
            now_vn = datetime.now(VIETNAM_TZ)
            timestamp = now_vn.isoformat()
            
            # 1. Ghi logs mới
            if current_logs:
                docs_to_insert = []
                for doc in current_logs:
                    if not isinstance(doc, dict):
                        continue
                    # Clone document to avoid modifying the in-memory cache
                    doc_copy = dict(doc)
                    doc_copy.pop('_id', None)
                    doc_copy['debug_logged_at'] = timestamp
                    docs_to_insert.append(doc_copy)

                if docs_to_insert:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        None,
                        lambda: debug_logs_collection.insert_many(docs_to_insert)
                    )
            
            # 2. Xóa logs cũ hơn 7 tiếng
            cutoff_time = (now_vn - timedelta(hours=7)).isoformat()
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: debug_logs_collection.delete_many({"debug_logged_at": {"$lt": cutoff_time}})
            )
        except Exception as e:
            print(f"✗ Error in debug_logs_monitoring_task: {e}")


@app.on_event("startup")
async def startup_event():
    """Preload cache từ MongoDB, khởi động background tasks, seed admin role & account"""
    _init_redis_cache()
    
    # Seeding defaults
    try:
        # 1. Seed admin role
        admin_role = roles_collection.find_one({"role_key": "admin"})
        if not admin_role:
            roles_collection.insert_one({
                "role_key": "admin",
                "name": "Admin",
                "description": "Quản trị viên toàn quyền hệ thống",
                "permissions": ["Tổng quan", "SRT", "Thông số Stream", "URL & Key", "FFmpeg", "Thống kê", "Vmix Monitor", "ViewSync", "Speedtest", "Debug Log", "Tài khoản", "Phân quyền"],
                "created_at": datetime.now(VIETNAM_TZ).isoformat()
            })
            print("✓ Seeded default admin role successfully!")

        # 2. Seed master admin user
        admin_user = accounts_collection.find_one({"username_key": "admin"})
        admin_hash = hashlib.sha256("admin123".encode("utf-8")).hexdigest()
        if not admin_user:
            accounts_collection.insert_one({
                "username": "admin",
                "username_key": "admin",
                "password": "admin123",
                "password_hash": admin_hash,
                "role": "admin",
                "created_at": datetime.now(VIETNAM_TZ).isoformat(),
                "email": "admin@vmix.monitor",
                "phone": "0123456789",
                "is_locked": False
            })
            print("✓ Seeded master admin account successfully!")
        else:
            # Force role and lock state to make sure admin is always admin and unlocked
            accounts_collection.update_one(
                {"username_key": "admin"},
                {"$set": {"role": "admin", "is_locked": False, "password": "admin123", "password_hash": admin_hash}}
            )
    except Exception as seed_err:
        print(f"✗ Seeding roles/admin failed: {seed_err}")

    loop = asyncio.get_event_loop()
    try:
        docs = await loop.run_in_executor(
            None,
            lambda: list(collection.find().sort("last_updated", DESCENDING).limit(500))
        )
        for doc in docs:
            name = doc.get("name")
            if name:
                _data_cache[name] = _to_json_safe(doc)
        print(f"✓ Cache preloaded: {len(_data_cache)} machines from MongoDB")
    except Exception as e:
        print(f"✗ Cache preload error: {e}")

    # Preload WAN IP bandwidth cache for today
    try:
        today_str = datetime.now(VIETNAM_TZ).strftime("%d-%m-%Y")
        wan_docs = await loop.run_in_executor(
            None,
            lambda: list(bandwidth_collection.find({"date": today_str}))
        )
        for doc in wan_docs:
            ipwan = doc.get("ipwan")
            if ipwan:
                _ipwan_bandwidth_cache[ipwan] = {
                    "date": today_str,
                    "sender_max": float(doc.get("sender_max", 0.0)),
                    "receiver_max": float(doc.get("receiver_max", 0.0)),
                    "sender_min": float(doc.get("sender_min", 0.0)),
                    "receiver_min": float(doc.get("receiver_min", 0.0))
                }
        print(f"✓ WAN IP bandwidth cache preloaded: {len(_ipwan_bandwidth_cache)} IPs for date {today_str}")
    except Exception as preload_err:
        print(f"✗ WAN IP bandwidth cache preload error: {preload_err}")

    asyncio.create_task(check_inactive_machines())
    asyncio.create_task(flush_statistics_from_cache())
    asyncio.create_task(rollup_statistics_scheduler())
    asyncio.create_task(ipwan_bandwidth_monitor_task())
    asyncio.create_task(_daily_cleanup_task()) # Chạy task dọn dẹp 3h sáng
    asyncio.create_task(debug_logs_monitoring_task())
    print("✓ Background task started: Auto-OFF inactive machines (1 min timeout)")
    print(f"✓ Background task started: Statistics cache flush every {_stats_flush_interval_sec}s")
    print(f"✓ Background task started: Tiered rollup every {_TIERED_ROLLUP_INTERVAL_SEC}s (raw→1m→5m→15m→hours)")
    print("✓ Background task started: WAN IP Bandwidth monitoring every 3 minutes")
    print("✓ Background task started: Daily cleanup scheduled at 03:00 AM")
    print("✓ Background task started: Debug Logs collection writer every 3 seconds")


def run_server():
    import uvicorn

    def _supports_ansi_colors() -> bool:
        stream = getattr(sys, "stdout", None)
        if stream is None or not hasattr(stream, "isatty") or not stream.isatty():
            return False

        if os.environ.get("NO_COLOR"):
            return False
        if os.environ.get("FORCE_COLOR"):
            return True

        if os.name != "nt":
            return True

        # On Windows, ANSI support depends on the host terminal.
        return any([
            bool(os.environ.get("WT_SESSION")),
            bool(os.environ.get("ANSICON")),
            os.environ.get("ConEmuANSI", "").upper() == "ON",
            os.environ.get("TERM_PROGRAM", "").lower() == "vscode",
            bool(os.environ.get("TERM")),
        ])

    use_colors = _supports_ansi_colors()

    print(f"🚀 Starting WebSocket server on http://localhost:{PORT}")
    print(f"📡 WebSocket endpoint: ws://localhost:{PORT}/ws")
    print(f"🔌 REST API endpoint: http://localhost:{PORT}/")
    if not use_colors:
        print("ℹ ANSI colors are not supported on this console. Running logs without colors.")
    uvicorn.run(app, host="0.0.0.0", port=PORT, use_colors=use_colors)


def main():
    # Backend-only mode.
    run_server()


if __name__ == "__main__":
    main()
