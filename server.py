
import http.server
import socketserver
import json
from datetime import datetime
import threading
import sys
import os
from pymongo import MongoClient, DESCENDING
import requests

# Try to import from config.py, fallback to environment variables
try:
    from config import MONGODB_URI, DATABASE_NAME, COLLECTION_NAME, DISCORD_WEBHOOK, PREFIX
except ImportError:
    MONGODB_URI = os.getenv('MONGODB_URI', '')
    DATABASE_NAME = os.getenv('DATABASE_NAME', 'vmix_monitor')
    COLLECTION_NAME = os.getenv('COLLECTION_NAME', 'logs')
    DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK', '')
    PREFIX = os.getenv('PREFIX', 'SRT')

# Port configuration - support Render's dynamic port
PORT = int(os.getenv('PORT', 8088))

# Kết nối MongoDB với TLS
try:
    client = MongoClient(
        MONGODB_URI, 
        serverSelectionTimeoutMS=10000,
        tls=True,
        tlsAllowInvalidCertificates=True
    )
    db = client[DATABASE_NAME]
    collection = db[COLLECTION_NAME]
    # Test connection
    client.admin.command('ping')
    print("✓ Đã kết nối MongoDB thành công!")
except Exception as e:
    print(f"✗ Lỗi kết nối MongoDB: {e}")
    print(f"Kiểm tra lại:")
    print("  1. Mật khẩu trong config.py")
    print("  2. IP Address whitelist trên MongoDB Atlas")
    print("  3. Kết nối internet")
    sys.exit(1)

def send_discord_notification(name, ipwan, port, status):
    """Gửi thông báo lên Discord webhook"""
    try:
        message = f"[{PREFIX}][{name}] SRT {status} | IPWAN: {ipwan} | PORT: {port}"
        payload = {"content": message}
        resp = requests.post(DISCORD_WEBHOOK, json=payload, timeout=5)
        if resp.status_code in [200, 204]:
            print(f"✓ Discord notification sent: {name} - {status}")
        else:
            print(f"✗ Discord error: {resp.status_code}")
    except Exception as e:
        print(f"✗ Discord notification failed: {e}")

class VmixRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_HEAD(self):
        """Handle HEAD requests for health checks (UptimeRobot, etc.)"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests for health checks"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response = {
            "status": "online",
            "service": "vMix Monitor Server",
            "timestamp": datetime.now().isoformat()
        }
        self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def do_POST(self):
        # Kiểm tra path để phân biệt endpoint
        if self.path == '/update_name':
            self.handle_update_name()
            return
        
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            timestamp = datetime.now().isoformat()
            
            # Lấy name làm key để identify máy
            machine_name = data.get('name', data.get('ip', 'Unknown'))
            
            # Kiểm tra document cũ để phát hiện BẤT KỲ thay đổi nào
            existing = collection.find_one({"name": machine_name})
            has_changes = False
            changed_fields = []
            
            if existing:
                # So sánh từng field quan trọng (ngoại trừ timestamp)
                fields_to_check = ['ip', 'ipwan', 'status', 'port', 'name']
                for field in fields_to_check:
                    old_val = existing.get(field)
                    new_val = data.get(field)
                    if old_val != new_val:
                        has_changes = True
                        changed_fields.append(f"{field}: {old_val} → {new_val}")
            else:
                # Document mới = có thay đổi
                has_changes = True
                changed_fields.append("New machine")
            
            # Update hoặc insert (upsert) - Mỗi máy chỉ có 1 document
            document = {
                "name": machine_name,
                "ip": data.get('ip'),
                "ipwan": data.get('ipwan'),
                "status": data.get('status'),
                "port": data.get('port'),
                "timestamp": timestamp,
                "last_updated": timestamp
            }
            
            # Tìm theo name và update, nếu chưa có thì tạo mới
            result = collection.update_one(
                {"name": machine_name},
                {"$set": document},
                upsert=True
            )
            
            action = "Updated" if result.matched_count > 0 else "Inserted"
            print(f"✓ {action}: {machine_name} - {data.get('ip', 'N/A')}:{data.get('port', 'N/A')} - {data.get('status', 'N/A')}")
            
            # GHI CHÚ: Discord notification được xử lý bởi GUI (server_gui_advanced.py)
            # Không gửi ở đây để tránh duplicate
            if has_changes:
                print(f"  → Changes detected: {', '.join(changed_fields)}")
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "action": action}).encode('utf-8'))
        except Exception as e:
            print(f"✗ Lỗi xử lý POST: {e}")
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
    
    def handle_update_name(self):
        """Xử lý cập nhật tên máy"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            old_name = data.get('old_name')
            new_name = data.get('new_name')
            
            # Update tên trong MongoDB
            result = collection.update_one(
                {"name": old_name},
                {"$set": {"name": new_name, "last_updated": datetime.now().isoformat()}}
            )
            
            if result.matched_count > 0:
                print(f"✓ Đã đổi tên: {old_name} → {new_name}")
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok"}).encode('utf-8'))
            else:
                print(f"✗ Không tìm thấy: {old_name}")
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Not found"}).encode('utf-8'))
        except Exception as e:
            print(f"✗ Lỗi update tên: {e}")
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

    def do_GET(self):
        try:
            # Lấy tất cả máy (mỗi máy 1 document) từ MongoDB, sắp xếp theo thời gian update
            documents = collection.find().sort("last_updated", DESCENDING).limit(200)
            entries = []
            
            for doc in documents:
                # Format lại để tương thích với GUI cũ
                entry = {
                    "timestamp": doc.get("last_updated", doc.get("timestamp", "")),
                    "data": {
                        "name": doc.get("name", ""),
                        "ip": doc.get("ip", ""),
                        "ipwan": doc.get("ipwan", ""),
                        "status": doc.get("status", ""),
                        "port": doc.get("port", "")
                    }
                }
                entries.append(entry)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(entries, ensure_ascii=False).encode('utf-8'))
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

    def log_message(self, format, *args):
        # Ghi log ra stdout thay vì stderr
        sys.stdout.write("%s - - [%s] %s\n" %
                         (self.client_address[0],
                          self.log_date_time_string(),
                          format%args))

if __name__ == "__main__":
    from http.server import ThreadingHTTPServer
    # Bind to 0.0.0.0 to accept connections from anywhere (required for cloud deployment)
    server_address = ('0.0.0.0', PORT)
    httpd = ThreadingHTTPServer(server_address, VmixRequestHandler)
    print(f"Server starting on 0.0.0.0:{PORT}")
    print(f"MongoDB: {DATABASE_NAME}.{COLLECTION_NAME}")
    print(f"Prefix: {PREFIX}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()
