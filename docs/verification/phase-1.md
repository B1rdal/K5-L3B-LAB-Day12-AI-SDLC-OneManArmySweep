# Ma trận truy vết Phase 1

| AC | Cách kiểm chứng | Bằng chứng (link `docs/proof/phase-1/...`) | Kết quả (đạt / chưa đạt — ghi trung thực) |
|---|---|---|---|
| Gather movement và biên | `tests/test_smoke_p1.py` | `docs/proof/test-results.md` | đạt |
| Oxy, ngạt, faint | `test_oxygen_choke_faint_clears_inventory` | `docs/proof/test-results.md` | đạt |
| Hái và bắt cá | `test_harvest_and_catch_update_hold` | `docs/proof/test-results.md` | đạt |
| Kho gather → quan | `test_inv_01_gather_writes_inventory_quan_reads_it` | `docs/proof/test-results.md` | đạt |

## Đánh giá ngắn
- Yêu cầu đạt: vòng gather, inventory, CLI và tính tất định.
- Điều cần chỉnh cho phase sau: hoàn thiện vòng đời khách và phục vụ tại quán.
