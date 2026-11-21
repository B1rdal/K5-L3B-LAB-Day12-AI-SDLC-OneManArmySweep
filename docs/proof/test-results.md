# Kết quả kiểm chứng

- Ngày: 2026-11-21
- Môi trường: Windows, Python 3.15.2
- Lệnh: `python3 -m unittest discover -s tests -v`
- Kết quả: 45 test đã chạy, 45 test đạt.
- Phạm vi: CLI, contract, JSONL tất định, input, movement, inventory item/freshness, live server, gather, cá sấu, quán, day loop, shop, pause, soak và team-checker unit test.
- Benchmark: `docs/proof/phase-4/bench.json` — 61,0 FPS trung bình, 58,0 FPS 1% low trong 30 giây.
- Soak: `docs/proof/phase-4/soak.json` — hoàn thành 10 ngày, 0 crash.
