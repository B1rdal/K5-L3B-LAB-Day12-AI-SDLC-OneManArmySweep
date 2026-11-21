# Deterministic demo

Sử dụng sau khi thay đổi RNG, thứ tự entity hoặc vòng tick.

1. Chạy cùng một lệnh headless hai lần với cùng mode, seed, scenario và inputs.
2. So sánh hai file JSONL theo byte.
3. Nếu khác, kiểm tra đồng hồ hệ thống, random toàn cục, iteration không sắp xếp và ID allocation.
4. Chạy lại toàn bộ test sau khi sửa.
