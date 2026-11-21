# Ma trận truy vết Phase 3

| Yêu cầu | Kiểm chứng | Kết quả |
|---|---|---|
| Inventory item `{id, kind, fresh}` | `tests/test_inventory.py`, contract integration | Đạt |
| Từ chối schema đếm cũ với mã thoát 2 | `test_v12_rejects_counted_inventory` | Đạt |
| Độ tươi giảm theo phase và phát `spoiled` đúng một lần | `test_crossing_30_emits_spoiled_at_tick_one` | Đạt |
| Khách giữ item theo ID, ưu tiên item tươi | `test_scheduled_customer_reserves_stock` và unit test quan | Đạt |
| Giá bán theo độ tươi trung bình | `test_customer_cook_serve_and_pay` | Đạt |
| Output cùng seed giống từng byte | `test_con_02_deterministic_bytes` | Đạt |

Thay đổi schema là breaking change có chủ ý của Contract v1.2; quyết định được ghi tại `docs/adr/0001-individual-inventory.md`.
