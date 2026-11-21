# Day 12 — AI SDLC: Quán Ăn Chợ Nổi

**Bài làm:** Đào Đức Sơn — 2A202604105 (`B1rdal`)

Game mô phỏng một ngày của Út Sen: thu thập nguyên liệu dưới sông, phục vụ quán ăn và mua nâng cấp cho ngày kế tiếp. Bản triển khai dùng Python 3, không cần thư viện ngoài, có giao diện trình duyệt và chế độ headless tất định để chấm tự động.

## Chạy nhanh

Yêu cầu: Python 3.12 trở lên.

```bash
python3 -m unittest discover -s tests -v
python3 -m chonoi.live --mode day
python3 -m chonoi.headless --mode day --seed 42 --days 1 --ticks 50000 --out day.jsonl
```

Mở địa chỉ được in sau lệnh `live`. Điều khiển: WASD hoặc phím mũi tên để di chuyển, `E` tương tác, `Space` bắt cá, `P`/`Esc` tạm dừng, `H` bật tương phản cao, `R` chơi lại. Trong shop, dùng phím số để mua nâng cấp và nút hoàn tất để sang ngày mới.

## Nội dung đã hoàn thành

- Phase 1: CLI/headless tất định, movement, input, scenario, JSONL và inventory nguyên tử.
- Phase 2: sáu loại nguyên liệu, cá di chuyển/sinh mới, cá sấu tuần tra–truy đuổi, hai bếp, bốn bàn, sáu món, kế hoạch D1–D5, shop và nâng cấp oxy/Máu.
- Phase 3: từng vật phẩm có `id`, `kind`, `fresh`; độ tươi giảm theo phase, đồ hỏng dưới 30, giữ nguyên liệu theo ID và giá bán theo độ tươi trung bình.
- Phase 4: pause, cảnh báo HUD, chế độ tương phản cao, benchmark 30 giây và soak 10 ngày.

Thông số chuẩn nằm trong [`game.contract.json`](game.contract.json). Mô tả lệnh và kiến trúc chi tiết nằm ở [`docs/STARTER.md`](docs/STARTER.md); ma trận kiểm chứng nằm trong `docs/verification/`.

## Lệnh kiểm chứng

```bash
python3 -m unittest discover -s tests -v
python3 -m chonoi.bench --seed 42 --duration 30 --out docs/proof/phase-4/bench.json
python3 -m chonoi.soak --seed 42 --days 10 --out docs/proof/phase-4/soak.json
```

Kết quả hiện tại: 45/45 test đạt, benchmark trung bình 61 FPS, 1% low 58 FPS, soak hoàn thành 10/10 ngày và 0 crash.

## Giới hạn đã biết

- `extensions` để trống; toàn bộ phần bắt buộc được ưu tiên.
- Đồ họa dùng hình khối tự tạo trong trình duyệt, không dùng asset bên ngoài.

## Hồ sơ

[`TEAM.md`](TEAM.md) · [`CHANGELOG.md`](CHANGELOG.md) · [`CREDITS.md`](CREDITS.md) · [`docs/clarify.md`](docs/clarify.md) · [`docs/ai-usage-log.md`](docs/ai-usage-log.md) · [`docs/retro.md`](docs/retro.md) · [`docs/members/B1rdal.md`](docs/members/B1rdal.md)
