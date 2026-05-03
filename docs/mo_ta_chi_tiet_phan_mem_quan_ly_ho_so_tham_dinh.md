# Mô tả chi tiết phần mềm quản lý hồ sơ thẩm định giá

Ngày lập: 01/05/2026  
Mục đích tài liệu: cung cấp cho đối tác thiết kế UI/UX, tư vấn sản phẩm hoặc đội phát triển tiếp theo một bức tranh đầy đủ về hiện trạng phần mềm, luồng nghiệp vụ, kiến trúc kỹ thuật và các hướng phát triển nên cân nhắc.

## 1. Tổng quan sản phẩm

Phần mềm được xây dựng để hỗ trợ tự động hóa quy trình quản lý hồ sơ thẩm định giá tài sản, đặc biệt là các hồ sơ có giấy chứng nhận quyền sử dụng đất, hồ sơ vay vốn ngân hàng, hợp đồng dịch vụ thẩm định giá, phiếu yêu cầu thẩm định giá, biên bản nghiệm thu và các chứng từ thanh toán.

Mục tiêu chính của phần mềm là giảm thao tác nhập liệu thủ công, giảm lỗi khi điền biểu mẫu Word/Excel, quản lý tập trung hồ sơ trên SQLite, theo dõi doanh thu/công nợ và chuẩn hóa việc xuất bộ hồ sơ để lưu trữ hoặc gửi nội bộ.

Phần mềm hiện được triển khai dưới dạng ứng dụng Streamlit chạy cục bộ trên máy tính Windows. Dữ liệu chính được lưu trong SQLite; file gốc, Word, PDF và ZIP được lưu trong thư mục hồ sơ theo từng hợp đồng.

## 2. Nhóm người dùng mục tiêu

Người dùng chính hiện tại là cá nhân hoặc bộ phận nghiệp vụ thẩm định giá sử dụng nội bộ. Phần mềm đã bỏ phân quyền vì đang phục vụ một người dùng chính, nhưng cấu trúc chức năng vẫn đủ để mở rộng cho nhiều người dùng trong tương lai nếu cần.

Các nhóm có thể sử dụng trong tương lai:

- Chuyên viên tiếp nhận và nhập hồ sơ.
- Chuyên viên nghiệp vụ/thẩm định viên.
- Bộ phận kế toán theo dõi phí, thanh toán và công nợ.
- Quản lý phòng/chi nhánh xem dashboard doanh thu.
- Bộ phận hành chính quản lý mẫu Word.
- Đối tác UI/UX hoặc đội phát triển phần mềm nâng cấp sản phẩm.

## 3. Luồng nghiệp vụ tổng thể

### 3.1. Luồng tạo hồ sơ mới

1. Người dùng mở màn hình Nhập/Quét hồ sơ.
2. Tải lên file PDF hoặc ảnh giấy chứng nhận quyền sử dụng đất.
3. Phần mềm hiển thị tài liệu trong khung xem, có thumbnail từng trang, zoom, xoay trang và tự động xoay theo hướng chữ viết.
4. Người dùng chạy OCR toàn bộ tài liệu bằng AI online, hiện ưu tiên Gemini API.
5. AI trích xuất dữ liệu chính từ GCN:
   - Số thửa đất.
   - Số tờ bản đồ.
   - Địa chỉ thửa đất.
   - Tên chủ sở hữu cuối cùng.
   - Địa chỉ chủ sở hữu.
   - Số CCCD/CMND.
6. Dữ liệu OCR tự điền sang form nhập liệu.
7. Người dùng bổ sung thông tin nghiệp vụ:
   - Số hợp đồng.
   - Loại khách hàng.
   - Nguồn/ngân hàng.
   - Mục đích thẩm định.
   - Phí thẩm định.
   - Tạm ứng, chi phí khảo sát.
   - Ghi chú cá nhân.
   - Các thông tin đại diện, mã số thuế, người nhận bàn giao nếu là khách hàng tổ chức.
8. Người dùng lưu hồ sơ vào SQLite.
9. File gốc PDF/ảnh được lưu vào thư mục hồ sơ.
10. Người dùng xuất Excel, Word, PDF hoặc ZIP khi cần.

### 3.2. Luồng quản lý hồ sơ đã lưu

1. Người dùng mở trang Quản lý hồ sơ.
2. Bảng hồ sơ hiển thị dữ liệu từ SQLite.
3. Người dùng tìm kiếm động theo:
   - Số hợp đồng.
   - Tên khách hàng.
   - Số CCCD.
   - Nguồn/ngân hàng.
   - Ghi chú cá nhân.
4. Người dùng lọc nâng cao theo:
   - Tháng thực hiện.
   - Trạng thái thanh toán.
   - Trạng thái hồ sơ.
   - Nguồn/ngân hàng.
   - Loại khách hàng.
   - Chuyên viên.
5. Người dùng có thể thao tác trực tiếp trên bảng:
   - Xem/xuất hồ sơ.
   - Sửa hồ sơ bằng popup.
   - Đổi trạng thái thanh toán.
   - Hủy hoặc khôi phục hồ sơ.
   - Chọn nhiều hồ sơ để hủy/khôi phục hàng loạt.
6. Bảng có thể tùy chỉnh cột hiển thị và độ rộng cột. Cấu hình độ rộng cột được lưu lại cho phiên sử dụng sau.
7. Người dùng có thể xuất đúng bảng đang lọc ra Excel.

### 3.3. Luồng xuất bộ hồ sơ

1. Người dùng bấm nút xem/xuất ở một hồ sơ.
2. Popup xuất hồ sơ mở ra.
3. Người dùng chọn hoặc nhập thư mục lưu bộ hồ sơ. Đường dẫn được lưu lại cho lần xuất sau.
4. Thư mục hồ sơ được đặt tên theo quy tắc:
   - `Số hợp đồng - Tên khách hàng`
   - Không gắn ID vào tên folder.
   - Ví dụ: `010-2026-N04-1027-DN - Ông Nguyễn Huy Hoàng`
5. File Word/PDF được xuất trực tiếp trong thư mục hồ sơ, không tạo thư mục con `documents`.
6. File gốc được lưu trong thư mục con `originals`.
7. File ZIP được lưu trong thư mục con `package`.
8. Người dùng có thể:
   - Xem trước nội dung đã render.
   - So sánh preview với file Word đã xuất.
   - Xuất Word.
   - Duyệt và xuất PDF.
   - Đóng gói ZIP hồ sơ.
   - Mở nhanh thư mục xuất bằng Windows Explorer.

## 4. Các phân hệ chức năng hiện có

### 4.1. Dashboard

Dashboard cung cấp góc nhìn tổng quan về doanh thu và công nợ.

Chức năng chính:

- Lọc theo năm, tháng, nguồn/ngân hàng, loại khách hàng, chuyên viên và trạng thái hồ sơ.
- Thống kê doanh thu dự kiến.
- Thống kê doanh thu đã thanh toán.
- Thống kê công nợ/chưa thanh toán.
- Không tính hồ sơ hủy vào doanh thu và công nợ.
- Biểu đồ doanh thu theo tháng.
- Biểu đồ công nợ theo tháng.
- Bảng tổng hợp theo tháng.
- Bảng chi tiết công nợ/chưa thanh toán.
- Nút đánh dấu đã thanh toán ngay trong bảng công nợ.

Ý nghĩa nghiệp vụ:

- Giúp theo dõi hiệu quả kinh doanh theo tháng/năm.
- Giúp phát hiện các hồ sơ chưa thu tiền.
- Hỗ trợ kế toán hoặc quản lý ưu tiên thu hồi công nợ.

### 4.2. Nhập/Quét hồ sơ

Đây là phân hệ hỗ trợ tạo hồ sơ mới từ tài liệu đầu vào.

Chức năng tài liệu:

- Tải lên PDF hoặc ảnh.
- Xem nhiều trang PDF.
- Thumbnail sidebar để nhảy nhanh đến từng trang.
- Chọn thumbnail để hiển thị đúng trang được chọn.
- Xem 1 trang hoặc 2 trang liên tiếp.
- Zoom in/zoom out.
- Xoay trái/xoay phải.
- Tự động xoay từng trang theo hướng chữ viết.
- Ghi nhớ góc xoay auto/manual theo từng trang trong session.
- Khóa góc xoay từng trang để tránh auto-rotate ghi đè.
- Cảnh báo khi hệ thống tự xoay 180° hoặc 270°.

Chức năng OCR:

- Chỉ dùng OCR toàn bộ tài liệu.
- Đã bỏ OCR trang đang xem và OCR vùng chọn theo yêu cầu.
- Hỗ trợ Gemini API.
- Có cấu hình lưu API Key từ lần sử dụng trước.
- Trích xuất dữ liệu GCN vào các trường:
  - Số thửa đất.
  - Số tờ bản đồ.
  - Địa chỉ thửa đất.
  - Tên chủ sở hữu cuối cùng.
  - Địa chỉ chủ sở hữu.
  - Số CCCD/CMND.
- Dữ liệu OCR tự đồng bộ vào form nhập liệu theo thời gian thực.

Chức năng form:

- Form nhập liệu tiếng Việt có dấu.
- Tự điền dữ liệu từ OCR.
- Có danh sách chọn lấy từ file Excel mẫu.
- Có chức năng thêm/sửa danh sách chọn ngay trong app.
- Tháng thực hiện tự xác định theo thời gian hiện tại.
- Trạng thái hồ sơ mặc định là Đang xử lý.
- Trạng thái thanh toán mặc định là Chưa thanh toán đối với hồ sơ mới.
- Một số trường nghiệp vụ không cần nhập trong phần bổ sung được để mặc định khi xuất Excel.

### 4.3. Quản lý hồ sơ

Phân hệ này là trung tâm quản lý hồ sơ đã lưu.

Chức năng bảng:

- Hiển thị danh mục hồ sơ từ SQLite.
- Bảng thao tác gọn theo phong cách Figma, dùng icon thay cho nút chữ dài.
- Cột thao tác thu gọn gồm xem, sửa, thanh toán, hủy.
- Badge trạng thái thanh toán:
  - Đã thanh toán.
  - Chưa thanh toán.
- Badge trạng thái hồ sơ:
  - Đang xử lý.
  - Hủy.
- Màu cảnh báo riêng cho hồ sơ hủy.
- Hiển thị số CCCD.
- Hiển thị ghi chú cá nhân.
- Cho phép điều chỉnh độ rộng cột.
- Lưu lại tùy chỉnh độ rộng cột ở phiên làm việc gần nhất.
- Cho phép chọn cột hiển thị/ẩn.
- Sắp xếp theo tháng thực hiện, phí, khách hàng, số hợp đồng.
- Tìm kiếm động, không phân biệt chữ hoa/thường.
- Tìm kiếm theo ghi chú cá nhân.
- Xuất đúng bảng đang lọc ra Excel.

Chức năng popup sửa hồ sơ:

- Sửa thông tin khách hàng.
- Sửa số hợp đồng.
- Sửa ngày hợp đồng.
- Sửa ngày chứng thư.
- Sửa phí thẩm định.
- Sửa nguồn/ngân hàng.
- Sửa mục đích thẩm định.
- Sửa tài sản thẩm định.
- Sửa thông tin tổ chức: mã số thuế, đại diện, chức vụ, căn cứ ủy quyền.
- Sửa thông tin người nhận bàn giao.
- Nút xuất nhanh hồ sơ ngay trong popup sửa.

Chức năng hủy/khôi phục:

- Hủy hồ sơ nhanh ngay trong bảng.
- Batch action hủy/khôi phục nhiều hồ sơ.
- Hồ sơ hủy không tính vào doanh thu.
- Hồ sơ hủy không tính vào công nợ.
- Có shortcut lọc nhanh chỉ xem hồ sơ hủy.
- Đã bỏ tính năng lý do hủy theo yêu cầu hiện tại.

### 4.4. Quản lý template Word

Phân hệ này quản lý các mẫu Word dùng để xuất hồ sơ.

Chức năng chính:

- Quản lý đường dẫn template cá nhân và tổ chức.
- Xem danh sách placeholder trong từng mẫu.
- Kiểm tra thiếu placeholder bắt buộc theo từng mẫu.
- Báo lỗi rõ nếu thiếu mẫu bắt buộc hoặc thiếu placeholder bắt buộc.
- Xem trước nội dung template đã render.
- So sánh preview với file Word đã xuất.
- Placeholder editor trong app để sửa nhanh nội dung mẫu.
- Lịch sử chỉnh sửa template.
- Khôi phục phiên bản template từ lịch sử.
- Gắn nhãn template:
  - production.
  - draft.
  - testing.
- Khóa template production để tránh sửa nhầm.

Lưu ý hiện tại:

- Phân quyền đã được bỏ vì phần mềm đang dùng cá nhân.
- Template vẫn cần được quản lý cẩn thận vì ảnh hưởng trực tiếp tới hợp đồng và chứng từ phát hành.

### 4.5. Xuất Word/PDF/ZIP

Phần mềm hiện hỗ trợ hai nhóm khách hàng:

- Khách hàng cá nhân.
- Khách hàng tổ chức/doanh nghiệp.

Bộ hồ sơ cá nhân hiện gồm:

- Hợp đồng dịch vụ thẩm định giá.
- Phiếu yêu cầu thẩm định giá tài sản.
- Biên bản nghiệm thu.

Bộ hồ sơ tổ chức hiện gồm:

- Hợp đồng.
- Biên bản nghiệm thu/thanh lý.
- Đề nghị thanh toán.
- Thư chào phí.

Chức năng xuất:

- Render placeholder từ dữ liệu SQLite.
- Giữ định dạng Word tốt hơn khi thay thế placeholder.
- Xem trước nội dung render theo giao diện gần giống Word.
- Xuất Word.
- Xuất PDF tự động sau khi duyệt bằng LibreOffice/soffice.
- Đóng gói ZIP gồm:
  - File gốc trong `originals`.
  - Word/PDF ở thư mục gốc hồ sơ.
  - Không đóng gói lặp lại file ZIP cũ trong `package`.
- Cho phép chọn đường dẫn lưu bộ hồ sơ.
- Tự lưu đường dẫn cho lần xuất sau.
- Có nút mở thư mục xuất.

Quy tắc thư mục xuất hiện tại:

- Folder hồ sơ: `Số hợp đồng - Tên khách hàng`.
- Không gắn ID hồ sơ vào tên folder.
- Không tạo thư mục con `documents`.
- File gốc nằm trong `originals`.
- File ZIP nằm trong `package`.

### 4.6. Import dữ liệu Excel cũ

Phần mềm hỗ trợ nhập dữ liệu từ file Excel theo dõi cũ vào SQLite.

Chức năng:

- Đọc file nhiều sheet.
- Hỗ trợ file `.xlsm` có macro.
- Chỉ lấy các sheet có cấu trúc dữ liệu import được.
- Chỉ lấy dữ liệu cần thiết theo form hiện có.
- Tự nhận diện tháng thực hiện từ tên sheet hoặc số hợp đồng.
- Tránh import trùng hồ sơ.
- Dữ liệu sau import có thể tìm kiếm, lọc, thống kê và xuất hồ sơ.

## 5. Dữ liệu đang quản lý

Dữ liệu chính lưu trong SQLite gồm các nhóm trường:

Thông tin định danh hồ sơ:

- ID nội bộ.
- Số hợp đồng.
- Ngày hợp đồng.
- Ngày chứng thư.
- Tháng thực hiện.
- Loại khách hàng.
- Trạng thái hồ sơ.
- Trạng thái thanh toán.
- Thư mục hồ sơ.
- File gốc.

Thông tin khách hàng:

- Tên khách hàng.
- Địa chỉ khách hàng.
- Số CCCD/CMND.
- Mã số thuế.
- Người đại diện.
- Chức vụ người đại diện.
- Căn cứ ủy quyền.

Thông tin tài sản:

- Loại tài sản.
- Mô tả tài sản thẩm định.
- Số thửa đất.
- Số tờ bản đồ.
- Địa chỉ thửa đất.
- Chủ sở hữu.

Thông tin nghiệp vụ:

- Mục đích thẩm định.
- Nguồn/ngân hàng.
- Phí thẩm định.
- Tạm ứng.
- Còn lại thanh toán.
- Chi phí khảo sát.
- Chuyên viên.
- Ghi chú cá nhân.

Thông tin xuất hồ sơ:

- Template cá nhân/tổ chức.
- Placeholder render.
- Lịch sử template.
- Cấu hình thư mục xuất.

## 6. Placeholder Word quan trọng

Các placeholder đang được dùng trong mẫu Word gồm:

- `{{TEN_KHACH_HANG}}`
- `{{DIA_CHI_KHACH_HANG}}`
- `{{CCCD}}`
- `{{DIEN_THOAI_KHACH_HANG}}`
- `{{TAI_SAN_THAM_DINH}}`
- `{{DIA_CHI_TAI_SAN}}`
- `{{MUC_DICH_THAM_DINH}}`
- `{{MUC_DICH_THAM_DINH_DAY_DU}}`
- `{{MUC_DICH_THAM_DINH_RUT_GON}}`
- `{{NGUON}}`
- `{{SO_HOP_DONG}}`
- `{{SO_HOP_DONG_VAN_BAN}}`
- `{{NGAY_HOP_DONG}}`
- `{{NGAY_HOP_DONG_PLEIKU}}`
- `{{NGAY_CHUNG_THU}}`
- `{{SO_BIEN_BAN_NGHIEM_THU}}`
- `{{SO_DE_NGHI_THANH_TOAN}}`
- `{{PHI_THAM_DINH}}`
- `{{PHI_THAM_DINH_BANG_CHU}}`
- `{{TAM_UNG}}`
- `{{CON_LAI_THANH_TOAN}}`
- `{{MA_SO_THUE}}`
- `{{NGUOI_DAI_DIEN}}`
- `{{CHUC_VU_NGUOI_DAI_DIEN}}`
- `{{CAN_CU_UY_QUYEN}}`
- `{{NGUOI_NHAN_BAN_GIAO}}`
- `{{CHUC_VU_NGUOI_NHAN_BAN_GIAO}}`
- `{{SDT_NGUOI_NHAN_BAN_GIAO}}`

Một số quy tắc render đã xử lý:

- Số tiền bằng chữ có dấu, ví dụ: `Bốn triệu bốn trăm ngàn đồng chẵn`.
- `VP Bank` được giữ bằng khoảng trắng không ngắt dòng để tránh Word tách giữa `VP` và `Bank`.
- Mục đích rút gọn trong Phiếu yêu cầu bỏ đoạn “Làm cơ sở tham khảo để”.
- Địa điểm khảo sát tài sản ưu tiên dùng địa chỉ thửa đất.
- Ngày Phiếu yêu cầu dùng cùng ngày với ngày hợp đồng.
- Không tự ghép thêm thông tin nguồn/ngân hàng nếu mục đích đã có cụm “ngân hàng”.

## 7. Kiến trúc kỹ thuật hiện tại

### 7.1. Công nghệ

- Python.
- Streamlit cho giao diện.
- SQLite cho cơ sở dữ liệu.
- OpenPyXL cho đọc/ghi Excel.
- python-docx cho đọc/ghi Word.
- LibreOffice/soffice để chuyển Word sang PDF.
- Gemini API cho OCR AI online.
- Một số logic xử lý ảnh/PDF để preview, xoay trang và OCR.

### 7.2. Cấu trúc mã nguồn

Các thành phần chính:

- `app.py`: file khởi động chính.
- `views/`: các màn hình giao diện.
  - `dashboard.py`.
  - `entry.py`.
  - `entry_viewer.py`.
  - `entry_ocr.py`.
  - `entry_form.py`.
  - `cases.py`.
  - `case_table.py`.
  - `case_dialogs.py`.
  - `case_documents.py`.
  - `templates.py`.
  - `template_list.py`.
  - `template_editor.py`.
  - `template_history.py`.
  - `settings.py`.
  - `sidebar.py`.
- `src/`: logic nghiệp vụ.
  - `sqlite_store.py`.
  - `case_filters.py`.
  - `case_exports.py`.
  - `case_files.py`.
  - `case_packager.py`.
  - `document_exporter.py`.
  - `pdf_exporter.py`.
  - `excel_writer.py`.
  - `template_manager.py`.
  - `case_output_preferences.py`.
  - Các module OCR/preview/model liên quan.
- `samples/templates/`: mẫu Word cá nhân và tổ chức.
- `data/`: SQLite, cấu hình app, cấu hình AI, lịch sử template, file hồ sơ.
- `tests/`: bộ test tự động.

### 7.3. Kiểm thử hiện tại

Phần mềm đã có test tự động cho các nhóm chức năng:

- SQLite CRUD: tạo, sửa, xóa hồ sơ.
- Import Excel nhiều sheet.
- Import `.xlsm` có macro.
- Bộ lọc hồ sơ.
- Báo cáo công nợ.
- Xuất bảng theo bộ lọc.
- OCR action bằng mock AI.
- Luồng OCR toàn bộ tài liệu -> tự điền form -> lưu SQLite.
- Xuất Excel sau OCR.
- Lưu file gốc PDF/ảnh vào thư mục hồ sơ.
- Tránh ghi đè khi lưu 2 file gốc cùng tên.
- Xuất Word/PDF/ZIP từ hồ sơ SQLite mẫu.
- Bộ template cá nhân/tổ chức.
- ZIP không đóng gói lặp file ZIP cũ.
- Placeholder render đúng trong Word.
- Báo lỗi rõ khi thiếu template hoặc thiếu placeholder.
- Preview và file Word xuất khớp nội dung.
- Template editor paragraph/table/header/footer.
- Lịch sử/restore template.
- Không còn import phân quyền sau khi bỏ tính năng phân quyền.

Số test gần nhất: 52 test pass.

## 8. Hiện trạng UI/UX

Giao diện hiện đã chuyển sang tiếng Việt có dấu và đang dần áp dụng theo thiết kế Figma do người dùng cung cấp.

Các điểm đã cải thiện:

- Top navigation.
- Dashboard có KPI, biểu đồ, bảng công nợ.
- Bảng quản lý hồ sơ gọn hơn, nhiều thao tác bằng icon.
- Popup xem/xuất hồ sơ.
- Popup sửa hồ sơ.
- Template management có danh sách, editor, lịch sử.
- Khung nhập/quét hồ sơ chia hai vùng: xem tài liệu và form nhập liệu.

Các điểm nên nhờ đối tác UI/UX tư vấn:

- Tổ chức lại navigation cho nhóm nghiệp vụ thường dùng.
- Tối ưu bảng hồ sơ khi số lượng cột lớn.
- Thiết kế pattern cho popup sửa/xuất hồ sơ.
- Thiết kế trạng thái OCR và độ tin cậy dữ liệu.
- Thiết kế trải nghiệm xem PDF nhiều trang.
- Thiết kế dashboard chuyên nghiệp hơn cho quản lý doanh thu.
- Chuẩn hóa badge trạng thái, màu cảnh báo và icon.
- Thiết kế flow quản lý template an toàn nhưng không quá phức tạp.
- Thiết kế trải nghiệm chọn thư mục xuất phù hợp với ứng dụng desktop/local.

## 9. Những vấn đề đã xử lý gần đây

- Sửa lỗi xuất Excel với merged cell read-only.
- Sửa lỗi encoding tiếng Việt trong một số màn hình.
- Sửa lỗi nút mở trang PDF.
- Sửa auto-rotate theo từng trang.
- Sửa chọn thumbnail PDF hiển thị đúng trang.
- Bỏ OCR trang đang xem và OCR vùng chọn.
- Lưu API key từ lần sử dụng trước.
- Chuyển database từ Excel sang SQLite.
- Import lại dữ liệu tháng 03/2026, 04/2026.
- Sửa tìm kiếm không phân biệt hoa/thường.
- Thêm tìm kiếm động.
- Thêm tìm kiếm theo ghi chú cá nhân.
- Thêm cột số CCCD.
- Thêm điều chỉnh độ rộng cột và lưu cấu hình.
- Chuyển khối xem/xuất thành popup.
- Thêm ngày hợp đồng, ngày chứng thư vào popup sửa hồ sơ.
- Thêm xuất nhanh hồ sơ trong popup sửa.
- Cải thiện preview Word có định dạng.
- Sửa lỗi template thiếu placeholder sau khi chuẩn hóa mục đích.
- Sửa lỗi điện thoại bị lặp trong mẫu Word.
- Sửa lỗi dư dấu chấm trong mẫu Word.
- Sửa mục đích PYC bị thừa thông tin nguồn/ngân hàng.
- Sửa tiền bằng chữ không dấu.
- Đổi quy tắc folder xuất theo số hợp đồng và tên khách hàng.

## 10. Giới hạn hiện tại

Một số giới hạn cần đối tác nắm:

- Ứng dụng hiện chạy local bằng Streamlit, chưa phải sản phẩm web production nhiều người dùng.
- Chưa có đăng nhập/phân quyền vì người dùng hiện dùng cá nhân.
- Chưa có cơ chế backup tự động SQLite và thư mục file.
- OCR phụ thuộc chất lượng tài liệu và API Gemini.
- Cần kiểm soát chi phí API nếu dùng thường xuyên.
- Chọn thư mục hiện dùng ô nhập đường dẫn, chưa phải hộp thoại chọn folder native.
- Preview Word trong app chỉ mô phỏng định dạng, không thể thay thế hoàn toàn việc mở Word.
- Xuất PDF phụ thuộc LibreOffice/soffice cài trên máy.
- Một số mẫu Word nguồn nếu định dạng quá phức tạp có thể cần chuẩn hóa thêm.
- SQLite phù hợp dùng cá nhân hoặc nhóm nhỏ; nếu nhiều người dùng đồng thời nên cân nhắc PostgreSQL hoặc backend riêng.

## 11. Đề xuất hướng phát triển tiếp theo

### Giai đoạn 1: Ổn định bản local đang dùng

Mục tiêu: biến bản hiện tại thành công cụ nội bộ ổn định cho một người hoặc một nhóm nhỏ.

Nên làm:

- Chuẩn hóa toàn bộ template Word production.
- Hoàn thiện bộ placeholder chuẩn và tài liệu hướng dẫn sửa template.
- Thêm backup tự động:
  - SQLite.
  - Template.
  - Thư mục hồ sơ.
- Thêm màn hình kiểm tra sức khỏe hệ thống:
  - Đường dẫn SQLite.
  - Đường dẫn template.
  - Đường dẫn xuất.
  - LibreOffice.
  - API key OCR.
- Thêm log lỗi dễ đọc cho người dùng.
- Thêm nút mở file Word/PDF sau khi xuất.
- Thêm cơ chế version cho database schema.
- Đóng gói app thành bản chạy đơn giản hơn trên Windows.

### Giai đoạn 2: Nâng cấp UI/UX chuyên nghiệp

Mục tiêu: cải thiện trải nghiệm dùng hằng ngày, giảm thao tác và giảm lỗi.

Nên làm:

- Thiết kế lại toàn bộ layout theo Figma chuẩn.
- Xây dựng design system:
  - Màu.
  - Typography.
  - Button.
  - Input.
  - Table.
  - Dialog.
  - Badge.
  - Empty state.
  - Error state.
- Tối ưu dashboard cho quản lý.
- Tối ưu màn hình nhập hồ sơ cho tốc độ nhập liệu.
- Tối ưu bảng quản lý hồ sơ khi dữ liệu nhiều.
- Thiết kế workflow xuất hồ sơ rõ ràng theo các bước:
  - Chọn hồ sơ.
  - Kiểm tra dữ liệu.
  - Preview.
  - Xuất Word.
  - Duyệt PDF.
  - Đóng gói ZIP.
- Thiết kế cảnh báo dữ liệu thiếu trước khi xuất.

### Giai đoạn 3: Nâng cấp kiến trúc kỹ thuật

Mục tiêu: tách app khỏi giới hạn Streamlit local nếu muốn dùng cho team/công ty.

Phương án đề xuất:

- Backend API:
  - FastAPI hoặc Django.
  - PostgreSQL thay SQLite nếu nhiều người dùng.
  - Object storage hoặc file server để lưu tài liệu.
- Frontend:
  - React/Next.js hoặc một framework tương đương.
  - Áp dụng trực tiếp thiết kế UI/UX từ Figma.
- Worker xử lý nền:
  - OCR.
  - Xuất PDF.
  - Đóng gói ZIP.
  - Backup.
- Queue:
  - Celery/RQ hoặc job queue tương đương.
- Auth nếu dùng team:
  - Đăng nhập.
  - Vai trò.
  - Audit log.

### Giai đoạn 4: Tự động hóa nghiệp vụ sâu hơn

Mục tiêu: giảm thêm thao tác thủ công và tăng kiểm soát chất lượng.

Nên làm:

- OCR nhiều loại giấy tờ khác ngoài GCN.
- Tự phân loại tài sản.
- Tự đề xuất mục đích thẩm định theo nguồn/ngân hàng.
- Tự kiểm tra thiếu dữ liệu trước khi xuất hợp đồng.
- Tự kiểm tra logic:
  - Ngày hợp đồng.
  - Ngày chứng thư.
  - Phí.
  - Tạm ứng.
  - Công nợ.
  - Loại khách hàng.
- Tự sinh mã hồ sơ/số hợp đồng theo quy tắc.
- Tự tạo checklist pháp lý theo loại tài sản.
- Nhắc công nợ đến hạn/quá hạn.
- Tích hợp email/Zalo/Drive nếu công ty có nhu cầu.

## 12. Câu hỏi nên gửi đối tác tư vấn

Để đối tác tư vấn sát nhu cầu, nên hỏi rõ:

1. Nếu dùng nội bộ 1-3 người thì nên tiếp tục Streamlit local hay cần chuyển sang desktop app?
2. Nếu công ty dùng nhiều người, nên chuyển lên web app theo kiến trúc nào?
3. Với dữ liệu hồ sơ và giấy tờ pháp lý, nên tổ chức lưu file và backup thế nào?
4. Nên thiết kế UI nhập liệu theo wizard từng bước hay một màn hình chia đôi tài liệu/form?
5. Bảng quản lý hồ sơ nên tối ưu thế nào khi có hàng nghìn hồ sơ?
6. Dashboard nên có thêm chỉ số nào cho quản lý?
7. Quản lý template Word nên để người nghiệp vụ tự sửa đến mức nào?
8. Có nên giữ Word template hay chuyển sang engine tạo tài liệu khác?
9. OCR nên dùng Gemini API, OpenAI API, hay kết hợp thêm OCR truyền thống?
10. Nếu dùng cloud, cần tiêu chuẩn bảo mật và phân quyền nào?
11. Lộ trình phát triển nên chia mấy giai đoạn, chi phí và rủi ro từng giai đoạn?
12. Cần chuẩn hóa dữ liệu nguồn Excel cũ đến mức nào trước khi migrate chính thức?

## 13. Đề xuất ưu tiên ngắn hạn

Ưu tiên 1:

- Hoàn thiện template Word production.
- Thêm kiểm tra dữ liệu bắt buộc trước khi xuất.
- Thêm backup tự động.
- Đóng gói bản app local ổn định.

Ưu tiên 2:

- Thiết kế lại UI/UX theo Figma.
- Chuẩn hóa dashboard và bảng quản lý hồ sơ.
- Tối ưu popup sửa/xuất hồ sơ.

Ưu tiên 3:

- Đánh giá nhu cầu nhiều người dùng.
- Quyết định giữ local app hay chuyển sang web app.
- Nếu chuyển web app, thiết kế lại backend/database/file storage.

## 14. Kết luận

Phần mềm hiện đã vượt qua giai đoạn prototype đơn giản và có nhiều chức năng nghiệp vụ thực tế: OCR tài liệu, tự điền form, quản lý SQLite, dashboard doanh thu/công nợ, quản lý hồ sơ, quản lý template, xuất Word/PDF/ZIP và lưu trữ file theo hồ sơ.

Hướng phát triển tiếp theo nên tập trung vào ba việc:

- Ổn định bản local để dùng thật hằng ngày.
- Chuẩn hóa UI/UX để giảm thao tác và giảm lỗi.
- Đánh giá kiến trúc dài hạn nếu công ty muốn nhiều người dùng hoặc triển khai chính thức.

Tài liệu này có thể dùng làm đầu vào để đối tác UI/UX hoặc đội phát triển phân tích, báo giá, đề xuất roadmap và thiết kế bản nâng cấp tiếp theo.
