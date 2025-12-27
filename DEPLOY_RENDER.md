# Deploy vMix Monitor Server lên Render

## Cách 1: Deploy bằng GitHub (Khuyến nghị)

### Bước 1: Push code lên GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin <your-github-repo-url>
git push -u origin main
```

### Bước 2: Deploy trên Render
1. Truy cập https://render.com và đăng nhập
2. Click **New** → **Web Service**
3. Kết nối GitHub repository của bạn
4. Cấu hình:
   - **Name**: vmix-monitor-server
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python server.py`
   - **Instance Type**: Free

### Bước 3: Thêm Environment Variables
Trong phần **Environment**, thêm các biến:
- `MONGODB_URI` = `mongodb+srv://thanhhieu16082004:minhhieu16082004@cluster0.yars4po.mongodb.net/?appName=Cluster0`
- `DATABASE_NAME` = `vmix_monitor`
- `COLLECTION_NAME` = `logs`
- `DISCORD_WEBHOOK` = `https://discord.com/api/webhooks/1448559948408684669/s6plN6AIy9IFBo6coyNCF9YmmHIfIIVe-tEntpPnArRGI0JdIyl1pCz10rL5TyTP1JV6`
- `PREFIX` = `SRT`

### Bước 4: Deploy
- Click **Create Web Service**
- Render sẽ tự động build và deploy
- Sau khi deploy xong, bạn sẽ có URL dạng: `https://vmix-monitor-server.onrender.com`

## Cách 2: Deploy trực tiếp từ file

1. Tạo account tại https://render.com
2. Click **New** → **Web Service** → **Deploy without Git**
3. Upload folder này
4. Cấu hình như bước 2 và 3 ở trên

## Cấu hình MongoDB Atlas
**QUAN TRỌNG**: Phải whitelist IP của Render:
1. Vào MongoDB Atlas → Network Access
2. Click **Add IP Address**
3. Chọn **Allow Access from Anywhere** (0.0.0.0/0)
   Hoặc thêm IP cụ thể của Render

## Cập nhật URL trong Client
Sau khi deploy xong, sửa URL trong `vmix_monitor_gui.py`:
```python
url = "https://vmix-monitor-server.onrender.com"  # Thay bằng URL của bạn
```

## Test Server
```bash
curl -X POST https://vmix-monitor-server.onrender.com \
  -H "Content-Type: application/json" \
  -d '{"name":"TEST","ip":"192.168.1.1","ipwan":"1.2.3.4","status":"ON","port":22131}'
```

## Lưu ý
- **Free tier** của Render sẽ sleep sau 15 phút không hoạt động
- Request đầu tiên sau khi sleep sẽ mất ~30s để wake up
- Nếu cần server luôn online, nâng cấp lên plan trả phí
