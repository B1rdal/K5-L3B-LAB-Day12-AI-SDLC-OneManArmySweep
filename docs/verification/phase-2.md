# Ma trận truy vết Phase 2

| Yêu cầu | Kiểm chứng | Kết quả |
|---|---|---|
| Sáu nguyên liệu, N1–N6, 8 cá ban đầu | `game.contract.json`, `test_harvest_and_catch_update_hold` | Đạt |
| Cá di chuyển, đổi hướng, sinh mỗi 360 tick, tối đa 12 | `test_fish_move_turn_and_spawn` | Đạt |
| Cá sấu gây sát thương, rơi 50% giỏ LIFO, recoil | `test_monster_hit_drops_lifo_and_recoils` | Đạt |
| 2 bếp, 4 bàn, 6 món | `test_commands_and_contract_version`, contract | Đạt |
| Giữ nguyên liệu, nấu, bưng, phục vụ, thanh toán, tip | `test_scheduled_customer_reserves_stock`, `test_customer_cook_serve_and_pay` | Đạt |
| Gather → quán → shop → ngày mới | `test_day_transitions_and_upgrade_activates_next_day` | Đạt |
| D1–D5 và nâng cấp oxy/Máu áp dụng ngày sau | contract, `test_day_transitions_and_upgrade_activates_next_day` | Đạt |
| Pause dừng tick mô phỏng | `test_pause_stops_simulation_and_resume_runs_step` | Đạt |

Bằng chứng tổng hợp: `docs/proof/test-results.md`.
