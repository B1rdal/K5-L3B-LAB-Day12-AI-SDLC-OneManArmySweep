# Kế hoạch Phase 3 — Contract v1.2

- Thay inventory dạng số lượng bằng item riêng lẻ `{id, kind, fresh}`; từ chối rõ schema cũ.
- Giảm độ tươi 0,5/giây ở gather và 0,25/giây ở quán; đánh dấu hỏng khi dưới 30.
- Giữ nguyên liệu theo ID, ưu tiên đồ tươi; khi đồ giữ chỗ hỏng chỉ thử giữ lại một lần.
- Tính giá món theo độ tươi trung bình của các item thực tế đã nấu.
- Giữ tương thích hành vi Phase 1–2 và kiểm tra lại deterministic output.

Quyết định đổi schema và ảnh hưởng tích hợp được ghi tại `docs/adr/0001-individual-inventory.md`.
