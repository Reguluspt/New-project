# Inventory UI sau khi rà code

## Navigation cấp 1 trong `app.py`

- Dashboard: `views/dashboard.py`
- Nhập hồ sơ: `views/entry.py`
- Quản lý hồ sơ: `views/cases.py`
- Quản lý danh bạ tổ chức: `views/organizations_view.py`
- Danh bạ chuyển phát: `views/delivery_view.py`
- Sổ bộ: `views/sobo_view.py`
- Templates: `views/templates.py`, `views/template_list.py`, `views/template_editor.py`
- Cài đặt: `views/settings.py`

## Tab / flow cấp 2 bị thiếu trong bộ trước

### Nhập hồ sơ

- Upload nhiều PDF/ảnh GCN.
- OCR queue action.
- Viewer tài liệu.
- Form khách hàng cá nhân.
- Form khách hàng tổ chức.
- Thông tin nghiệp vụ.
- Expander thông tin GCN trích xuất từ AI.
- Checkbox chuyển tiếp cho nghiệp vụ.
- Action: lưu SQLite, xuất Excel, gửi mail yêu cầu định giá, gửi yêu cầu lên Web.
- Hồ sơ gần nhất.

### Quản lý hồ sơ

- Tab `Danh mục hồ sơ`.
- Tab `Doanh thu & Công nợ`.
- Expander hồ sơ từ Telegram/Mail Listener.
- Điều chỉnh độ rộng cột.
- Popup sửa hồ sơ.
- Popup xem và xuất hồ sơ.
- Preview Word, so sánh file đã xuất, duyệt PDF, đóng gói ZIP.
- Gửi mail yêu cầu định giá.
- Gửi yêu cầu lên Web.
- Phát hành chứng thư và chọn người nhận chuyển phát.

### Templates

- Hai nhóm mẫu: cá nhân và tổ chức.
- Bảng summary placeholder.
- Expander từng template.
- Nhãn phiên bản: production, draft, testing.
- Khóa/mở khóa production.
- Kiểm tra placeholder bắt buộc.
- Sửa nhanh block có placeholder.
- Lịch sử chỉnh sửa, snapshot và restore.

### Cài đặt

- Tab `Cấu hình Template`.
- Manager danh sách chọn trong Form Excel.
- Tab `Sức khỏe hệ thống`.
- Tab `Quản trị dữ liệu`.
- Sub-tab quản trị dữ liệu: Sao lưu, Khôi phục, Xóa trắng.
- Tab `Tích hợp OAuth2`.
- Google Workspace, Outlook Graph API, Outlook SMTP alias, mail Sổ bộ.

### Tổ chức

- Danh sách tổ chức.
- Radio thao tác: Thêm mới, Thêm từ Hợp đồng bằng AI, Cập nhật, Xóa.
- Upload hợp đồng hàng loạt và data editor kết quả AI.

### Danh bạ chuyển phát

- Data editor danh bạ người nhận phát hành chứng thư.
- Thêm/xóa/sửa dòng và lưu thay đổi.

### Sổ bộ

- Search/filter trạng thái.
- Đồng bộ Telegram.
- Kiểm tra Mail ngay.
- KPI chờ phản hồi, đã phản hồi, thời gian phản hồi TB.
- Card chi tiết yêu cầu sơ bộ.
- Mở bản đồ, tải GCN, xóa hồ sơ.
- Chế độ guest chỉ đọc.

## Bộ ảnh bổ sung

Các ảnh bổ sung nằm trong `outputs/premium_ui_redesign/full_tabs/`.
