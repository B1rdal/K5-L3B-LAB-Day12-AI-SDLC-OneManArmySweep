# ADR 0001 — Inventory theo từng vật phẩm

## Trạng thái

Đã chấp nhận cho Contract v1.2.

## Bối cảnh

Schema đếm theo loại không thể biểu diễn độ tươi riêng, item được khách giữ chỗ hoặc nguyên liệu thực tế đã dùng cho một món.

## Quyết định

Inventory dùng danh sách item `{id, kind, fresh}`. ID là duy nhất và ổn định; mọi thao tác giữ chỗ, hỏng và tiêu thụ dùng ID. Schema đếm cũ bị từ chối thay vì tự chuyển đổi ngầm.

## Hệ quả

Giá bán có thể tính từ độ tươi thật và việc giữ chỗ trở nên kiểm chứng được. File lớn hơn và đây là breaking change, nên producer/consumer phải nâng cấp cùng lúc. Validation và test tích hợp khóa schema mới.
