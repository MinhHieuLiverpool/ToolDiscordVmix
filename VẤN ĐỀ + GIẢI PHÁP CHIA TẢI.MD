## Capacity Notes (Render Free)

### Bối cảnh hệ thống
- 3 giao diện gọi API:
1. vMix Monitor GUI
2. ServerLogViewer (thường 1-2 user)
3. Web (nhiều user hơn)

### Thời gian chạy
- Nếu treo 14 giờ/ngày:
1. 30 ngày = 420 giờ/tháng
2. 31 ngày = 434 giờ/tháng
- Nếu quota free khoảng 750 giờ/tháng thì chưa chạm trần chỉ riêng service này.
- Lưu ý: chết server thường do tải đồng thời, không phải chỉ do số giờ bật.

### Điểm nghẽn chính hiện tại
1. Web realtime + all machines là nguồn tải nặng nhất.
2. WebSocket và polling đồng thời làm tăng tải DB.
3. vMix Monitor gửi theo port liên tục, số port cao sẽ đẩy write load lớn.

### Mốc rủi ro thực tế (ước lượng)
1. ServerLogViewer:
- 1-2 user: thường ổn
- 5-8 user: bắt đầu lag
- 10-15 user: dễ disconnect/reconnect

2. Web (realtime + all machines):
- Với khoảng 20-30 máy:
1. 3-5 user đã vào vùng nguy hiểm
2. 6-8 user dễ timeout/reconnect hàng loạt

3. vMix Monitor:
- Tính theo tổng port đang gửi:
1. 20-30 port: bắt đầu nóng
2. 40-60 port: rủi ro treo cao (đặc biệt khi có thêm Web realtime)

### Case cụ thể đã hỏi
- 2 Web + 2 ServerLogViewer + 30 port:
1. Là vùng nguy hiểm cao trên Render free
2. Có thể chạy được một lúc nhưng dễ gặp lag, timeout, reconnect
3. Nếu Web dùng daily mode hoặc single-machine thì ổn hơn đáng kể

### Các trường hợp xấu nhất
1. Nhiều user mở Web realtime all machines cùng lúc
2. Bão reconnect WebSocket khi mạng chập chờn/restart service
3. ServerLogViewer fallback sang REST polling hàng loạt
4. Nhiều port vMix gửi dày trong giờ cao điểm
5. Combo read/write peak cùng lúc (Web kéo + vMix đẩy)

### Giải pháp ưu tiên (theo thứ tự)
1. Tăng interval Web từ 5s lên 10-15s
2. Hạn chế realtime all machines cho user thường
3. Giới hạn số máy render/chart cùng lúc
4. Cache mạnh cho logs/statistics (RAM/Redis TTL ngắn)
5. WebSocket chỉ push từ cache và ưu tiên delta thay vì full payload
6. Thêm rate limit cho endpoint nặng
7. Giảm tần suất gửi từ vMix Monitor khi trạng thái ổn định
8. Bật backoff reconnect cho client
9. Thêm monitoring: CPU, RAM, p95, WS count, Mongo query
10. Nếu cần ổn định production: nâng gói hoặc tách service