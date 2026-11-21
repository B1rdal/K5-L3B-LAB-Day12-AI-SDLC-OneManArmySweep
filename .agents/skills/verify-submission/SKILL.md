# Verify submission

Sử dụng trước khi tích hợp, gắn tag hoặc release.

1. Chạy `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tests:. python3 -m unittest discover -s tests -v`.
2. Chạy `python3 tools/check_team.py` và báo riêng tiêu chí nhân sự.
3. Chạy `git status --short` để liệt kê đúng các file chưa commit.
4. Không sửa test để che lỗi luật chơi.
