# Merge Queue — bật qua Settings, không phải file YAML

GitHub Merge Queue bật ở: Settings → Rules/Branches → develop → 
"Require merge queue". Không có file cấu hình trong repo; đây là ghi chú.

Vì sao cần: nhiều PR cùng xanh KHÔNG đảm bảo merge cùng lúc an toàn. Merge queue
xếp hàng, ghép từng PR lên trạng thái đã-có-các-PR-trước, chạy lại CI, rồi merge
tuần tự. Đây là thứ biến "song song" thành "tích hợp an toàn".

Cấu hình đề xuất cho develop:
  - Require merge queue: ON
  - Build concurrency: 3-5 (số PR test đồng thời trong hàng)
  - Only merge if checks pass: ON
  - Merge method: Squash
