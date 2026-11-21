# Quán Ăn Chợ Nổi v1.0.0

## Điểm mới

- Một vòng ngày hoàn chỉnh: gather → quán → shop, với kế hoạch D1–D5 lặp lại.
- Sáu nguyên liệu, cá di chuyển/sinh mới, Cá Sấu Năm Chèo, hai bếp, bốn bàn và sáu món.
- Inventory theo từng vật phẩm với ID và độ tươi xuyên suốt các phase.
- Nâng cấp oxy/Máu, pause, cảnh báo dễ nhận biết và chế độ tương phản cao.
- Headless tất định, benchmark 30 giây và soak 10 ngày.

## Chạy

Yêu cầu Python 3.12 trở lên. Giải nén gói, mở terminal trong thư mục và chạy:

```bash
python3 -m unittest discover -s tests -v
python3 -m chonoi.live --mode day
```

Mở địa chỉ được in ra. Điều khiển bằng WASD/phím mũi tên, `E`, `Space`, `P`/`Esc`, `H` và `R`.

## Giới hạn đã biết

- Bản nộp là bài cá nhân nên không đáp ứng tiêu chí hành chính 4–6 thành viên.
- Không triển khai extension tùy chọn.
- Giao diện dùng hình khối tự tạo và không có asset âm thanh/đồ họa bên ngoài.
