from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
from datetime import datetime, timedelta
from collections import deque
import pytz
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
PORT = int(os.getenv('PORT', 8000))
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
    accounts_collection = db['web_accounts']
    statistics_collection = db['statistics']
    statistics_ts_collection = db[STATISTICS_TS_COLLECTION]
    statistics_hours_collection = db['statistic_hours']
    accounts_collection.create_index("username_key", unique=True)
    statistics_collection.create_index("id", unique=True)
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
    """Get all logs – served from MongoDB, not cache"""
    entries = []
    try:
        docs = list(collection.find().sort("last_updated", DESCENDING).limit(500))
        for doc in docs:
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
                    "cpu":       doc.get("temperature", doc.get("cpu")),
                    "memory":    doc.get("memory", doc.get("ram")),
                    "gpu":       doc.get("gpu"),
                    "sender_mbps": doc.get("sender_mbps"),
                    "receiver_mbps": doc.get("receiver_mbps"),
                    "vmix_recording": doc.get("vmix_recording", False),
                    "vmix_streaming": doc.get("vmix_streaming", False),
                    "vmix_external":  doc.get("vmix_external", False),
                    "resolution":     doc.get("resolution", "—"),
                    "srt_quality":    doc.get("srt_quality", "—"),
                    "srt_off_time": doc.get("srt_off_time", ""),
                }
            }
            entries.append(entry)
    except Exception as e:
        print(f"✗ MongoDB read error: {e}")
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
            "temperature": data.get('temperature', data.get('cpu')),
            "memory":      data.get('memory', data.get('ram')),
            "gpu":         data.get('gpu', data.get('gpu_percent')),
            "sender_mbps": data.get('sender_mbps'),
            "receiver_mbps": data.get('receiver_mbps'),
            "vmix_recording": data.get('vmix_recording', False),
            "vmix_streaming": data.get('vmix_streaming', False),
            "vmix_external":  data.get('vmix_external', False),
            "resolution":     data.get('resolution', '—'),
            "srt_quality":    data.get('srt_quality', '—'),
            "last_updated": timestamp,
            "timestamp":   timestamp,
        }
        _data_cache[machine_name] = document

        ip_val = data.get('ip', '')
        port_val = data.get('port', '')
        statistics_id = _build_statistics_id(ip_val, port_val, machine_name)

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
            "statistics_id": statistics_id,
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

async def _mongo_append_statistics(statistics_id: str, cpu_value, ram_value, timestamp: str):
    """Append CPU/RAM sample to statistics collection and keep a bounded history."""
    sample = {
        "cpu": cpu_value,
        "ram": ram_value,
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


async def _mongo_insert_statistics_ts(statistics_id: str, cpu_value, ram_value, timestamp: str):
    """Insert one CPU/RAM sample into MongoDB time series collection."""
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
                {"_id": 0, "cpu": 1, "ram": 1, "time": 1, "ts": 1},
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


def _bucket_10m(dt: datetime):
    return dt.replace(minute=(dt.minute // 10) * 10, second=0, microsecond=0)


async def _rollup_statistics_10m():
    """
    Aggregate closed 10-minute buckets from statistics -> statistic_hours,
    then remove processed points from statistics.
    """
    loop = asyncio.get_event_loop()
    now_vn = datetime.now(VIETNAM_TZ)
    current_bucket_start = _bucket_10m(now_vn)
    run_stamp = now_vn.isoformat()

    def _worker():
        docs = list(statistics_collection.find({}, {"_id": 0, "id": 1, "data": 1}))
        total_rollup_rows = 0
        total_samples_pruned = 0

        for doc in docs:
            statistics_id = doc.get("id", "")
            samples = doc.get("data", [])
            if not statistics_id or not isinstance(samples, list) or not samples:
                continue

            buckets = {}
            remaining_samples = []
            processed_samples = 0

            for sample in samples:
                if not isinstance(sample, dict):
                    remaining_samples.append(sample)
                    continue

                sample_dt = _parse_sample_time(sample.get("time"))
                if not sample_dt:
                    remaining_samples.append(sample)
                    continue

                bucket_start = _bucket_10m(sample_dt)

                # Keep the current (open) bucket, process only closed buckets.
                if bucket_start >= current_bucket_start:
                    remaining_samples.append(sample)
                    continue

                bucket = buckets.setdefault(bucket_start, {
                    "cpu_sum": 0.0,
                    "cpu_count": 0,
                    "ram_sum": 0.0,
                    "ram_count": 0,
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

                bucket["sample_count"] += 1
                processed_samples += 1

            if not buckets:
                continue

            rollup_rows = 0
            new_rows = []
            for bucket_start in sorted(buckets.keys()):
                agg = buckets[bucket_start]
                window_end = bucket_start + timedelta(minutes=10)
                avg_cpu = round(agg["cpu_sum"] / agg["cpu_count"], 2) if agg["cpu_count"] else None
                avg_ram = round(agg["ram_sum"] / agg["ram_count"], 2) if agg["ram_count"] else None

                row = {
                    "window_start": bucket_start.isoformat(),
                    "window_end": window_end.isoformat(),
                    "avg_cpu": avg_cpu,
                    "avg_ram": avg_ram,
                    "samples": agg["sample_count"],
                    "cpu_points": agg["cpu_count"],
                    "ram_points": agg["ram_count"],
                    "calculated_at": run_stamp,
                }
                new_rows.append(row)
                rollup_rows += 1

            # Merge theo window_start để giữ format: {id, data:[avg objects...]}
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

            if _redis_enabled and _redis_client is not None:
                _redis_client.delete(_redis_key_stats_raw(statistics_id))
                if remaining_samples:
                    encoded_remaining = [_redis_serialize(s) for s in remaining_samples if isinstance(s, dict)]
                    if encoded_remaining:
                        _redis_client.rpush(_redis_key_stats_raw(statistics_id), *encoded_remaining)
                _redis_client.set(_redis_key_stats_updated(statistics_id), run_stamp)
                _redis_client.sadd(_redis_stats_ids_key, statistics_id)

                rolled_doc = {
                    "id": statistics_id,
                    "data": merged_data,
                    "updated_at": run_stamp,
                }
                _redis_client.set(_redis_key_stat_hours(statistics_id), _redis_serialize(rolled_doc))
                _redis_client.sadd(_redis_stat_hours_ids_key, statistics_id)

            statistics_collection.update_one(
                {"id": statistics_id},
                {"$set": {"data": remaining_samples, "updated_at": run_stamp}},
            )

            total_rollup_rows += rollup_rows
            total_samples_pruned += processed_samples
            print(
                f"📊 Rollup 10m [{statistics_id}] windows={rollup_rows} samples={processed_samples} "
                f"remaining={len(remaining_samples)}"
            )

        return total_rollup_rows, total_samples_pruned

    try:
        rows, samples = await loop.run_in_executor(None, _worker)
        if rows > 0 or samples > 0:
            print(f"✓ Rollup 10m done: windows={rows}, samples_pruned={samples}")
    except Exception as e:
        print(f"✗ Rollup 10m error: {e}")


async def rollup_statistics_scheduler():
    """Run 10-minute rollup aligned to wall-clock buckets."""
    # Run once on startup to flush any already-closed windows.
    await _rollup_statistics_10m()

    while True:
        try:
            now_vn = datetime.now(VIETNAM_TZ)
            next_tick = _bucket_10m(now_vn) + timedelta(minutes=10)
            sleep_seconds = max(1.0, (next_tick - now_vn).total_seconds())
            await asyncio.sleep(sleep_seconds)
            await _rollup_statistics_10m()
        except Exception as e:
            print(f"✗ Rollup scheduler error: {e}")
            await asyncio.sleep(10)

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
                    "statusapp": doc.get("statusapp", 0),
                    "ping": doc.get("ping"),
                    "ping_timeouts": doc.get("ping_timeouts", 0),
                    "cpu": doc.get("temperature", doc.get("cpu")),
                    "memory": doc.get("memory", doc.get("ram")),
                    "gpu": doc.get("gpu"),
                    "sender_mbps": doc.get("sender_mbps"),
                    "receiver_mbps": doc.get("receiver_mbps"),
                    "vmix_recording": doc.get("vmix_recording", False),
                    "vmix_streaming": doc.get("vmix_streaming", False),
                    "vmix_external": doc.get("vmix_external", False),
                    "resolution": doc.get("resolution", "—"),
                    "srt_quality": doc.get("srt_quality", "—"),
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
                {"_id": 0, "username": 1, "password": 1, "created_at": 1}
            ).sort("username", 1)
        )
        return JSONResponse(content=docs)
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
            {"_id": 0, "username": 1, "password": 1, "password_hash": 1},
        )
        if not doc:
            return JSONResponse(content={"success": False, "message": "invalid credentials"}, status_code=401)

        provided_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
        stored_plain = str(doc.get("password", ""))
        stored_hash = str(doc.get("password_hash", ""))

        valid = hmac.compare_digest(stored_plain, password) or hmac.compare_digest(stored_hash, provided_hash)
        if not valid:
            return JSONResponse(content={"success": False, "message": "invalid credentials"}, status_code=401)

        return JSONResponse(content={"success": True, "username": doc.get("username", username)})
    except Exception as e:
        print(f"✗ Login account error: {e}")
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)

@app.post("/create_account")
async def create_account(payload: dict):
    """Tạo tài khoản web mới."""
    try:
        username = str(payload.get("username", "")).strip()
        password = str(payload.get("password", "")).strip()

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
                    {"$set": {"password": password, "password_hash": password_hash}}
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
            })
        except Exception:
            return JSONResponse(content={"success": False, "message": "username already exists"}, status_code=409)

        return JSONResponse(content={"success": True, "username": username, "created_at": created_at}, status_code=201)
    except Exception as e:
        print(f"✗ Create account error: {e}")
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)

@app.post("/delete_account")
async def delete_account(payload: dict):
    """Xóa tài khoản web theo username."""
    try:
        username = str(payload.get("username", "")).strip()
        if not username:
            return JSONResponse(content={"success": False, "message": "username is required"}, status_code=400)

        result = accounts_collection.delete_one({"username_key": username.lower()})
        if result.deleted_count > 0:
            return JSONResponse(content={"success": True, "deleted": 1, "username": username})
        return JSONResponse(content={"success": False, "deleted": 0, "message": "account not found"}, status_code=404)
    except Exception as e:
        print(f"✗ Delete account error: {e}")
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
                        port_candidates.append(port_int)
                    return collection.find_one(
                        {"ip": ip_text, "port": {"$in": port_candidates}},
                        {
                            "_id": 0,
                            "temperature": 1,
                            "memory": 1,
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
                latest_sample = {
                    "cpu": latest_cpu,
                    "ram": latest_ram,
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

                statistics_id = _build_statistics_id(doc.get("ip"), doc.get("port"), machine_name)
                cpu_value = doc.get("temperature", doc.get("cpu"))
                ram_value = doc.get("memory", doc.get("ram"))

                sample = {
                    "cpu": cpu_value,
                    "ram": ram_value,
                    "time": timestamp,
                }

                bucket = _realtime_stats_cache.get(statistics_id)
                if bucket is None:
                    bucket = deque(maxlen=_realtime_stats_max_points)
                    _realtime_stats_cache[statistics_id] = bucket
                bucket.append(sample)
                _realtime_stats_updated[statistics_id] = timestamp

                asyncio.create_task(_mongo_append_statistics(statistics_id, cpu_value, ram_value, timestamp))
                asyncio.create_task(_mongo_insert_statistics_ts(statistics_id, cpu_value, ram_value, timestamp))
                asyncio.create_task(_redis_append_statistics_sample(statistics_id, sample, timestamp))
        except Exception as e:
            print(f"✗ Error in flush_statistics_from_cache: {e}")

@app.on_event("startup")
async def startup_event():
    """Preload cache từ MongoDB, khởi động background tasks"""
    _init_redis_cache()
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
    asyncio.create_task(flush_statistics_from_cache())
    asyncio.create_task(rollup_statistics_scheduler())
    print("✓ Background task started: Auto-OFF inactive machines (1 min timeout)")
    print(f"✓ Background task started: Statistics cache flush every {_stats_flush_interval_sec}s")
    print("✓ Background task started: 10-minute statistics rollup")

if __name__ == "__main__":
    import uvicorn
    print(f"🚀 Starting WebSocket server on http://localhost:{PORT}")
    print(f"📡 WebSocket endpoint: ws://localhost:{PORT}/ws")
    print(f"🔌 REST API endpoint: http://localhost:{PORT}/")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
