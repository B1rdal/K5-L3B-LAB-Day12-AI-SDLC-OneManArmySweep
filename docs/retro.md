# Retro nhóm

## Phase 2 (nhanh)
- Điều tốt: mô phỏng headless và live dùng chung một lớp nên không lệch luật.
- Điều tệ: yêu cầu chi tiết theo phase phải được trích từ artifact ngoài repository.
- 1 hành động cho Phase 3: khóa hành vi bằng test scenario nhỏ trước khi mở rộng validation.

## Phase 4 (cuối)
- Rà lại hành động Phase 2: đã làm; các vòng gather và quan có test riêng.
- Điều tốt / điều tệ: 45 test, benchmark và soak chạy xanh; thời gian triển khai theo phase còn hạn chế.
- Số liệu: 45/45 test, 61,0 FPS trung bình, 10/10 ngày soak, 0 crash; token không ghi nhận.
- Một rủi ro AI: diễn giải sai yêu cầu dài; giảm rủi ro bằng contract dữ liệu, test truy vết và artifact đo được.
- Nếu làm lại: lấy đầy đủ ticket trước khi bắt đầu và tách issue theo từng vòng chơi.
