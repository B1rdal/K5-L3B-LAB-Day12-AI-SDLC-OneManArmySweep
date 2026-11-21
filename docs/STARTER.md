# Hướng dẫn kỹ thuật

## Thành phần

- `chonoi/sim/gather.py`: di chuyển, oxy/Máu, cây, cá, cá sấu và inventory.
- `chonoi/sim/quan.py`: khách, giữ nguyên liệu, bếp, phục vụ, thanh toán và uy tín.
- `chonoi/sim/shop.py`: mua nâng cấp.
- `chonoi/sim/day.py`: điều phối gather → quán → shop qua nhiều ngày.
- `chonoi/runner.py`: tick, pause và chuẩn hóa event cho live/headless.
- `chonoi/web/index.html`: giao diện trình duyệt.

Tất cả thông số gameplay đọc từ `game.contract.json`. Ngẫu nhiên đi qua các stream có seed; collection được sắp theo ID để giữ output tất định.

## Chạy

```bash
python3 -m chonoi.live --mode day --seed 42
python3 -m chonoi.headless --mode gather --seed 42 --ticks 600 --out gather.jsonl --inventory-out inventory.json
python3 -m chonoi.headless --mode quan --seed 42 --ticks 1200 --inventory inventory.json --out quan.jsonl
python3 -m chonoi.headless --mode day --seed 42 --days 2 --ticks 100000 --out day.jsonl
```

`gather` và `quan` hỗ trợ scenario JSON để tạo ca kiểm thử. Input có thể được phát lại từ file JSON. Scenario hoặc inventory sai trả mã thoát 2.

## Inventory v1.2+

```json
{"items":[{"id":"I1","kind":"ca_loc","fresh":100}]}
```

Mỗi item có ID riêng; độ tươi giảm trong gather/quán và item dưới 30 được xem là hỏng. File được ghi nguyên tử khi gather kết thúc.

## Kiểm chứng Phase 4

```bash
python3 -m unittest discover -s tests -v
python3 -m chonoi.bench --seed 42 --duration 30 --out docs/proof/phase-4/bench.json
python3 -m chonoi.soak --seed 42 --days 10 --out docs/proof/phase-4/soak.json
```

UI và headless dùng chung lớp mô phỏng, nên thay đổi luật không cần được triển khai hai lần.
