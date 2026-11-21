# Hợp đồng tích hợp v1.3

1. Inventory dùng schema `{"items":[{"id":"I1","kind":"ca_loc","fresh":100}]}`. `id` là duy nhất, `kind` thuộc sáu nguyên liệu trong contract, `fresh` nằm trong `[0,100]`. Schema đếm cũ bị từ chối.
2. File inventory chỉ được thay nguyên tử khi gather kết thúc. Collection luôn sắp theo ID tự nhiên để output tất định.
3. UI chỉ đọc snapshot từ `GET /state`, gửi input qua `POST /input` và khởi động lại qua `POST /restart`; UI không sửa trạng thái mô phỏng.
4. Cả live và headless dùng cùng `GatherSim`, `QuanSim`, `ShopSim` và `DaySim`.
5. Độ tươi giảm 0,5/giây ở gather và 0,25/giây ở quan. Mỗi item chỉ phát `spoiled` một lần khi đi từ `>=30` xuống `<30`.
6. Khách giữ item theo ID, ưu tiên item tươi nhất. Nếu item giữ chỗ bị hỏng, hệ thống thử giữ lại đúng một lần. Giá cơ bản được nhân với độ tươi trung bình của nguyên liệu đã dùng.
7. Input nút dùng cạnh nhấn một lần. Pause dừng tick mô phỏng nhưng vẫn nhận lệnh resume. Nâng cấp mua ở shop chỉ có hiệu lực từ ngày kế tiếp.
8. Event JSONL có `tick`, `name`, `data`; chế độ day thêm `day` và `phase`. Cùng contract, scenario, input và seed phải tạo output giống từng byte.

Các event chính gồm `gather`, `fish_caught`, `fish_spawned`, `monster_hit`, `spoiled`, `gather_end`, `customer_arrived`, `cook_started`, `dish_ready`, `served`, `paid`, `quan_end`, `bought`, `shop_end`, `day_start` và `day_end`.
