# Audit UI hiện tại và hướng nâng cấp premium

## Phạm vi

Audit dựa trên 4 màn hình hiện có trong `design_stitch/stitch_software_interface_design`:

- Dashboard tổng quan
- Nhập / quét hồ sơ OCR
- Quản lý hồ sơ
- Quản lý template

Mục tiêu redesign: giữ nguyên chức năng và cấu trúc nghiệp vụ, nâng cấp giao diện thành app nội bộ premium, dễ quét dữ liệu, thao tác nhanh và ít nhầm lẫn.

## Vấn đề chính

1. Màu sắc đang phụ thuộc nhiều vào xanh dương bão hòa, tạo cảm giác SaaS mặc định và hơi lạnh so với phần mềm nghiệp vụ tài chính - hồ sơ.
2. Card trắng, border và shadow dùng lặp lại đồng đều, khiến cấp bậc thông tin chưa rõ: KPI, filter, bảng và lịch sử đều có cảm giác ngang nhau.
3. Typography chưa đủ sắc thái. Số liệu lớn chưa dùng tabular/monospace treatment nên dashboard chưa có chất dữ liệu cao cấp.
4. Dashboard có khoảng trắng lớn ở biểu đồ nhưng chưa có dữ liệu thị giác đủ mạnh; biểu đồ trống làm màn hình kém hoàn thiện.
5. Màn hình OCR chia đôi đúng chức năng nhưng viewer tài liệu, vùng AI, form và trạng thái đồng bộ chưa tạo được một "workflow" rõ ràng từ trái sang phải.
6. Quản lý hồ sơ đang dùng bảng rất rộng nhưng thiếu lớp thông tin phụ như quick stats, saved filter, trạng thái ưu tiên hoặc pending action.
7. Quản lý template có slide-over lịch sử hợp lý nhưng bảng template và timeline còn phẳng, các trạng thái production/draft/testing chưa đủ nổi bật.
8. Icon/nav dùng pattern phổ thông; active state chưa đủ tinh tế, search và account area còn rời.

## Hướng nâng cấp

1. Palette: chuyển sang nền ivory/stone, chữ ink đậm, accent emerald có kiểm soát, amber cho cảnh báo và red cho quá hạn.
2. Surface: giảm shadow chung chung, dùng panel có viền mảnh, lớp nền có grain/grid nhẹ, KPI dùng emphasis bằng layout và số liệu.
3. Typography: heading lớn hơn nhưng gọn, label nhỏ dùng tracking, số liệu dùng tabular numeric.
4. Layout: giữ top nav, tăng cảm giác product bằng command bar, filter strip, split panel và right rail thay vì card trôi rời.
5. Dashboard: biến chart thành cụm bar/line thật, thêm công nợ ưu tiên ngay trong màn hình.
6. OCR: viewer tài liệu lớn, thumbnail rõ, field AI có trạng thái confidence/manual edit, form final nằm trong panel riêng.
7. Hồ sơ: bảng vẫn là trung tâm, thêm action rail và summary strip để người dùng biết cần xử lý gì.
8. Template: giữ bảng + lịch sử, nâng timeline thành audit rail có version, actor và lock state rõ hơn.

## Không thay đổi chức năng

- Không đổi menu chính.
- Không bỏ filter, search, export, upload, sync, save, pagination.
- Không thay đổi luồng OCR, quản lý hồ sơ hoặc lịch sử template.
- Không thêm module mới ngoài thông tin hỗ trợ hiển thị cho các chức năng đã có.
