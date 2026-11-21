# Ma trận truy vết Phase 4

| Yêu cầu | Kiểm chứng | Kết quả |
|---|---|---|
| Full regression | `python3 -m unittest discover -s tests -v` | Đạt, 45/45 |
| Benchmark 30 giây, trung bình ≥60 FPS | `docs/proof/phase-4/bench.json` | Đạt, 61,0 FPS; 1% low 58,0 FPS |
| Soak 10 ngày không crash | `docs/proof/phase-4/soak.json` | Đạt, 10/10 ngày; 0 crash |
| Cảnh báo HUD và tương phản cao | Rà `chonoi/web/index.html` | Đạt |
| Contract khai `bench_cmd`, `soak_cmd` | `test_commands_and_contract_version` | Đạt |
| Hồ sơ plan, verification, clarify, AI log, retro, member | Rà repository | Đạt |
| Nhóm 4–6 người | `python3 tools/check_team.py` | Không đạt: bài cá nhân, 1 người thực tế |

Commit, tag và release chưa được tạo trong lượt triển khai này.
