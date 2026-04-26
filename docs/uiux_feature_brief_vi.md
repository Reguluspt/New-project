# Tài liệu tổng hợp tính năng phần mềm thẩm định hồ sơ

## 1. Mục tiêu sản phẩm

Phần mềm dùng để tự động hóa quy trình xử lý hồ sơ thẩm định tài sản/bất động sản trong môi trường vận hành nội bộ. Hệ thống hiện đã có logic nghiệp vụ và các tính năng cốt lõi; giai đoạn tiếp theo cần một đơn vị UI/UX thiết kế lại giao diện chuyên nghiệp, tối ưu cho người dùng nghiệp vụ.

Mục tiêu của giao diện mới:

- Rút ngắn thời gian nhập và xử lý hồ sơ.
- Giảm lỗi thao tác khi quét, nhập liệu, chỉnh sửa, xuất hồ sơ, theo dõi thanh toán.
- Giúp người dùng nhìn rõ trạng thái hồ sơ, doanh thu, công nợ.
- Tối ưu cho tác vụ xử lý nhiều hồ sơ liên tục trong ngày.
- Thiết kế đủ chuyên nghiệp để có thể bàn giao cho đội phát triển triển khai thành sản phẩm nội bộ dài hạn.

## 2. Đối tượng sử dụng

### 2.1. Nhóm người dùng chính

1. Nhân viên nhập liệu / xử lý hồ sơ
2. Chuyên viên kinh doanh
3. Chuyên viên nghiệp vụ / thẩm định
4. Người kiểm soát / quản lý hồ sơ
5. Người phụ trách template / tài liệu
6. Người duyệt xuất PDF / báo cáo / hồ sơ phát hành
7. Quản trị hệ thống nội bộ

### 2.2. Đặc điểm người dùng

- Dùng tiếng Việt có dấu.
- Thường xử lý dữ liệu dạng hành chính, biểu mẫu, hồ sơ scan, Word, Excel.
- Cần giao diện rõ ràng, ít gây nhầm lẫn, ít thao tác thừa.
- Phần lớn thao tác lặp đi lặp lại, cần tối ưu tốc độ thao tác và kiểm tra chéo.

## 3. Định vị sản phẩm

Đây là một phần mềm nội bộ phục vụ quy trình hồ sơ thẩm định, không phải landing page hay CRM bán hàng. Giao diện cần thiên về:

- dữ liệu dày nhưng dễ quét
- luồng thao tác nhiều bước
- nhiều biểu mẫu và tài liệu
- nhiều trạng thái hồ sơ
- khả năng kiểm tra chéo giữa dữ liệu quét, dữ liệu nhập tay, dữ liệu lưu hệ thống và tài liệu đầu ra

## 4. Kiến trúc màn hình cấp cao

Phần mềm hiện có 4 khu vực chức năng chính:

1. **Dashboard**
2. **Nhập / quét hồ sơ**
3. **Quản lý hồ sơ**
4. **Quản lý template**

Ngoài ra có:

- sidebar cấu hình AI và cấu hình import dữ liệu
- popup chỉnh sửa hồ sơ
- popup / khối preview tài liệu

## 5. Tóm tắt chức năng hiện có

### 5.1. Dashboard

Dashboard là màn hình tổng hợp điều hành.

Hiện có các khối chức năng:

- Chọn năm thống kê
- Lọc theo:
  - nguồn / ngân hàng
  - loại khách hàng
  - chuyên viên kinh doanh
- Chọn tháng theo dõi
- KPI:
  - doanh thu dự kiến cả năm
  - đã thanh toán cả năm
  - công nợ tồn cả năm
  - doanh thu dự kiến trong tháng
- Biểu đồ doanh thu cả năm theo tháng
- Biểu đồ công nợ theo tháng
- Bảng tổng hợp theo tháng:
  - tháng
  - số hồ sơ
  - doanh thu dự kiến
  - đã thanh toán
  - công nợ tồn
- Bảng báo cáo công nợ chi tiết

### 5.2. Nhập / quét hồ sơ

Đây là màn hình thao tác nghiệp vụ chính, gồm 2 phần:

1. **Tài liệu đầu vào**
2. **Form hồ sơ**

### 5.3. Quản lý hồ sơ

Đây là màn hình tra cứu, chỉnh sửa, lọc, xuất và theo dõi hồ sơ.

### 5.4. Quản lý template

Màn hình dành cho quản lý file mẫu Word/Excel, placeholder, quyền sửa, lịch sử chỉnh sửa, khóa production.

## 6. Mô tả chi tiết từng module

---

## 6A. Module Dashboard

### 6A.1. Mục tiêu

Cho phép quản lý nhìn ngay tình hình:

- doanh thu theo tháng
- doanh thu dự kiến trong tháng
- doanh thu đã thu
- công nợ còn tồn
- xu hướng theo năm
- danh sách hồ sơ chưa thanh toán

### 6A.2. Thành phần giao diện cần có

1. **Bộ lọc dashboard**
   - Năm
   - Tháng theo dõi
   - Nguồn / ngân hàng
   - Loại khách hàng
   - Chuyên viên kinh doanh

2. **Khối KPI**
   - Doanh thu dự kiến cả năm
   - Đã thanh toán cả năm
   - Công nợ tồn cả năm
   - Doanh thu dự kiến trong tháng
   - Đã thanh toán trong tháng
   - Chưa thanh toán trong tháng
   - Doanh thu đến thời điểm hiện tại

3. **Biểu đồ**
   - Biểu đồ doanh thu theo tháng trong năm
   - Biểu đồ công nợ theo tháng

4. **Bảng dữ liệu**
   - Bảng tổng hợp theo tháng
   - Bảng công nợ chi tiết

### 6A.3. Dữ liệu dùng cho dashboard

- `execution_month`
- `payment_status`
- `valuation_fee_number`
- `source`
- `customer_type`
- `business_staff`

### 6A.4. Logic nghiệp vụ

- **Doanh thu dự kiến** = tổng giá trị `Phí thẩm định`
- **Đã thanh toán** = tổng giá trị `Phí thẩm định` của hồ sơ có `Trạng thái thanh toán = Đã thanh toán`
- **Công nợ tồn** = doanh thu dự kiến - đã thanh toán

### 6A.5. Nhu cầu UI/UX

- Dashboard phải rõ ràng, không rối.
- KPI phải nổi bật, có phân cấp mạnh.
- Biểu đồ phải đọc được nhanh, màu sắc phân biệt rõ:
  - dự kiến
  - đã thanh toán
  - công nợ
- Bảng công nợ phải đủ rõ để phục vụ thu tiền.

---

## 6B. Module Nhập / quét hồ sơ

### 6B.1. Mục tiêu

Cho phép người dùng:

- tải file GCN dạng PDF/ảnh
- xem file
- OCR / AI trích xuất dữ liệu
- chỉnh sửa dữ liệu quét
- đồng bộ sang form hồ sơ
- lưu hồ sơ
- xuất form Excel

### 6B.2. Tài liệu đầu vào

Nguồn file:

- PDF scan
- ảnh JPG / PNG / JPEG / WEBP

### 6B.3. Chức năng viewer tài liệu

Hiện có:

- Xem PDF nhiều trang
- Chế độ xem 1 trang
- Chế độ xem 2 trang liên tiếp
- Thanh chọn trang
- Thumbnail sidebar theo từng trang PDF để nhảy nhanh
- Zoom in / zoom out
- Xoay trái / phải
- Auto rotate theo hướng chữ viết
- Nút auto xoay lại
- Ghi nhớ góc xoay auto/manual theo từng trang trong session
- Khóa góc xoay từng trang để OCR lại không đè góc xoay
- Cảnh báo khi auto xoay 180 hoặc 270 độ
- Crop vùng xem
- OCR riêng vùng đang chọn
- OCR theo từng trang PDF
- OCR trang trái / phải khi xem 2 trang

### 6B.4. AI OCR / trích xuất dữ liệu

Phần mềm hỗ trợ:

- Gemini API
- OpenAI API

Nhu cầu AI:

- đọc tài liệu scan
- trích xuất dữ liệu từ GCN
- cho phép người dùng kiểm tra lại

Các trường cần trích xuất chính:

- Số thửa đất
- Số tờ bản đồ
- Địa chỉ thửa đất
- Tên chủ sở hữu cuối cùng
- Địa chỉ người đó
- Số CCCD / CMND

### 6B.5. Khu vực dữ liệu trích xuất từ GCN

Người dùng có thể:

- xem dữ liệu AI đọc ra
- sửa tay lại từng trường
- OCR lại theo trang hoặc theo vùng
- đồng bộ sang form hồ sơ

### 6B.6. Đồng bộ dữ liệu

Hiện có:

- đồng bộ tự động theo thời gian thực giữa:
  - dữ liệu GCN
  - form nhập liệu

Cần UI rõ ràng để người dùng hiểu:

- trường nào đến từ AI
- trường nào người dùng đã sửa tay
- trường nào đang là dữ liệu cuối cùng để lưu hồ sơ

### 6B.7. Form hồ sơ

Các nhóm trường hiện có:

1. **Thông tin chung**
   - Loại khách hàng
   - Tháng thực hiện
   - Trạng thái thanh toán
   - Số hợp đồng

2. **Thông tin tài sản / GCN**
   - Số thửa đất
   - Số tờ bản đồ
   - Địa chỉ thửa đất
   - Chủ sở hữu cuối cùng
   - Loại tài sản
   - Tài sản thẩm định giá

3. **Thông tin khách hàng**
   - Thông tin khách hàng
   - Địa chỉ khách hàng
   - Số CCCD/CMND
   - Nguồn / ngân hàng

4. **Thông tin nghiệp vụ**
   - Phí thẩm định
   - Mục đích thẩm định
   - Sơ bộ
   - Thời gian dự kiến hoàn thành
   - Tạm ứng
   - Chi phí khảo sát
   - Chuyên viên kinh doanh
   - Chuyên viên nghiệp vụ
   - Kiểm soát
   - Liên hệ lấy pháp lý
   - Ghi chú cá nhân

5. **Thông tin khách hàng tổ chức**
   - Mã số thuế
   - Người đại diện
   - Chức vụ người đại diện
   - Căn cứ / giấy ủy quyền đại diện
   - Người nhận bàn giao
   - Chức vụ người nhận bàn giao
   - Điện thoại người nhận bàn giao

### 6B.8. Hành động từ màn hình nhập/quét

- Quét AI
- OCR từng trang / từng vùng
- Lưu hồ sơ vào SQLite
- Lưu file gốc vào thư mục hồ sơ
- Xuất form Excel

### 6B.9. Nhu cầu UI/UX

- Đây là màn hình quan trọng nhất của sản phẩm.
- Cần chia khu vực rất rõ:
  - trái: tài liệu nguồn
  - phải: dữ liệu đọc ra / form hồ sơ
- Cần ưu tiên thao tác sửa nhanh.
- Cần làm rõ trạng thái:
  - chưa quét
  - đang quét
  - quét xong
  - dữ liệu đã chỉnh tay
  - đã lưu

---

## 6C. Module Quản lý hồ sơ

### 6C.1. Mục tiêu

Cho phép:

- tra cứu hồ sơ
- lọc hồ sơ
- xem tất cả cột dữ liệu
- chỉnh sửa nhanh
- đổi trạng thái thanh toán nhanh
- xuất danh sách đang lọc ra Excel
- mở popup sửa chi tiết
- xuất bộ hồ sơ Word/PDF/ZIP

### 6C.2. Chức năng hiện có

1. **Tìm kiếm**
   - theo tên khách hàng
   - số hợp đồng
   - CCCD
   - địa chỉ
   - ngân hàng
   - text liên quan khác

2. **Bộ lọc**
   - Tháng thực hiện
   - Trạng thái thanh toán
   - Nguồn / ngân hàng
   - Loại khách hàng
   - Chuyên viên kinh doanh

3. **Sắp xếp**
   - Ngày tạo
   - Tháng thực hiện
   - Phí thẩm định
   - Khách hàng
   - Số hợp đồng
   - Trạng thái thanh toán
   - Nguồn / ngân hàng

4. **Phân trang**
   - chọn số dòng / trang
   - chuyển trang

5. **Bảng dữ liệu**
   - hiển thị tất cả cột
   - chọn cột cần hiển thị / ẩn hiện
   - kéo ngang để xem hết

6. **Xuất Excel**
   - xuất đúng tập hồ sơ đang lọc
   - bám theo cột đang hiển thị
   - bám theo thứ tự sắp xếp hiện tại

7. **Đổi nhanh trạng thái thanh toán**
   - đánh dấu đã thanh toán
   - đánh dấu chưa thanh toán

8. **Popup sửa hồ sơ**
   - mở từ nút `Sửa`
   - chỉnh toàn bộ thông tin hồ sơ
   - xóa hồ sơ có xác nhận

9. **Chọn hồ sơ để thao tác tài liệu**
   - xem trước
   - so sánh preview/file xuất
   - xuất Word
   - duyệt và xuất PDF
   - đóng gói ZIP

### 6C.3. Nhu cầu UI/UX

- Bảng hồ sơ cần rất mạnh về data-grid.
- Cần cảm giác làm việc như một công cụ nghiệp vụ chuyên nghiệp.
- Popup sửa hồ sơ phải rõ ràng, chia section tốt.
- Thao tác nhanh và thao tác sâu phải tách bạch.

---

## 6D. Module Xuất hồ sơ, Word, PDF, ZIP

### 6D.1. Hỗ trợ 2 loại khách hàng

1. Khách hàng cá nhân
2. Khách hàng tổ chức

### 6D.2. Tài liệu đầu ra đang hỗ trợ

#### Khách hàng cá nhân

- Hợp đồng
- Phiếu yêu cầu / đề nghị
- Biên bản nghiệm thu

#### Khách hàng tổ chức

- Hợp đồng
- Biên bản bàn giao / biên bản thanh lý
- Đề nghị thanh toán
- Thư chào phí

### 6D.3. Chức năng tài liệu

- Preview nội dung trước khi xuất
- So sánh preview với file Word đã xuất
- Xuất bộ Word
- Duyệt và xuất PDF tự động
- Đóng gói ZIP hồ sơ

### 6D.4. Cấu trúc lưu hồ sơ

Mỗi hồ sơ có thư mục riêng, ví dụ:

- `case_files/<id>_<so_hop_dong>/`
  - `originals/`
  - `documents/`
  - `package/`

### 6D.5. Thành phần UX cần lưu ý

- Trạng thái từng tài liệu:
  - chưa tạo
  - đã preview
  - đã xuất Word
  - đã duyệt PDF
  - đã đóng gói ZIP
- Cần lịch sử rõ ràng để tránh nhầm phiên bản

---

## 6E. Module Template

### 6E.1. Mục tiêu

Cho phép đội vận hành quản lý mẫu Word/Excel mà không cần sửa code.

### 6E.2. Tính năng hiện có

1. Cấu hình đường dẫn template
2. Quản lý mẫu riêng cho:
   - cá nhân
   - tổ chức
3. Chuẩn hóa placeholder Word
4. Xem placeholder có trong file
5. Kiểm tra placeholder bắt buộc
6. Báo lỗi nếu template thiếu placeholder
7. Placeholder editor ngay trong app
8. Lưu chỉnh sửa trực tiếp vào file template
9. Lịch sử chỉnh sửa template
10. Snapshot/backup version
11. Khôi phục template từ lịch sử
12. Gắn nhãn template:
    - production
    - draft
    - testing
13. Khóa template production
14. Mở khóa template

### 6E.3. Nhu cầu UI/UX

- Phải phân biệt thật rõ:
  - template production
  - template draft
  - template testing
- Chỉnh sửa template là thao tác rủi ro, cần design cẩn thận.
- History và restore phải rất dễ hiểu.

---

## 6F. Module Import dữ liệu cũ

### 6F.1. Mục tiêu

Import dữ liệu từ Excel nhiều sheet vào SQLite, chỉ lấy các cột cần thiết cho phần mềm.

### 6F.2. Tính năng hiện có

- Nhập file Excel/xlsm nhiều sheet
- Tự nhận diện sheet dữ liệu
- Bỏ qua sheet mẫu / sheet không phù hợp
- Chống import trùng
- Đưa dữ liệu về đúng cấu trúc hồ sơ đang dùng

### 6F.3. Dữ liệu được import

- khách hàng
- địa chỉ
- tài sản thẩm định
- mục đích thẩm định
- phí thẩm định
- số tiền bằng chữ
- số hợp đồng / diễn giải
- nguồn / ngân hàng
- chi phí khảo sát
- NVKD
- ghi chú
- tháng thực hiện
- trạng thái thanh toán

## 7. Dữ liệu và thực thể chính

Các thực thể hệ thống quan trọng:

1. Hồ sơ
2. Khách hàng
3. Tài sản / thông tin GCN
4. Tài liệu gốc
5. Tài liệu Word/PDF đã xuất
6. Template
7. Người thao tác cá nhân
8. Lịch sử chỉnh sửa template

## 8. Trạng thái nghiệp vụ cần thể hiện tốt trên UI

### 8.1. Trạng thái thanh toán

- Đã thanh toán
- Chưa thanh toán

### 8.2. Trạng thái template

- production
- draft
- testing
- locked / unlocked

### 8.3. Trạng thái tài liệu

- chưa preview
- đã preview
- đã xuất Word
- đã duyệt PDF
- đã đóng gói ZIP

### 8.4. Trạng thái dữ liệu quét

- chưa quét
- đang quét
- quét thành công
- đã chỉnh tay
- đã đồng bộ vào form

## 9. Yêu cầu UI/UX tổng thể

### 9.1. Tinh thần thiết kế

Giao diện cần mang cảm giác:

- nội bộ doanh nghiệp
- chuyên nghiệp
- dữ liệu đậm đặc nhưng dễ quét
- giảm thao tác
- rõ ràng hơn phần mềm hành chính thông thường

### 9.2. Ưu tiên thiết kế

1. Tốc độ thao tác
2. Dễ đọc dữ liệu
3. Giảm sai sót
4. Dễ kiểm soát trạng thái
5. Dễ mở rộng thêm tính năng

### 9.3. Loại giao diện phù hợp

Ưu tiên:

- desktop-first
- dùng tốt ở màn hình 1366px trở lên
- tối ưu tốt ở 1440px / 1920px

### 9.4. Các pattern UI cần chú trọng

- Sidebar điều hướng hoặc top navigation rõ ràng
- Data table mạnh
- Filter bar
- Sticky actions
- Popup / drawer chỉnh sửa
- Split view document viewer + form
- Dashboard với KPI + chart + table
- History / audit style panel

## 10. Những vấn đề UI/UX cần giải quyết

1. Làm sao để người dùng vừa xem tài liệu scan vừa nhập hồ sơ mà không rối.
2. Làm sao để phân biệt dữ liệu AI đọc ra và dữ liệu cuối cùng.
3. Làm sao để xử lý nhiều trường dữ liệu mà không khiến form quá dài và mệt.
4. Làm sao để bảng hồ sơ đủ mạnh mà vẫn dễ dùng.
5. Làm sao để quản lý template an toàn nhưng không khó thao tác.
6. Làm sao để dashboard thực sự hữu ích cho quản lý, không chỉ là biểu đồ trang trí.

## 11. Danh sách màn hình UI/UX cần thiết kế

Đề xuất công ty UI/UX thiết kế tối thiểu các màn sau:

1. Dashboard tổng quan
2. Màn hình nhập/quét hồ sơ
3. Màn hình viewer tài liệu + OCR
4. Màn hình form hồ sơ
5. Màn hình quản lý hồ sơ dạng data grid
6. Popup / drawer chỉnh sửa hồ sơ
7. Màn hình preview / xuất tài liệu
8. Màn hình dashboard công nợ
9. Màn hình quản lý template
10. Màn hình chỉnh sửa placeholder template
11. Màn hình lịch sử template / restore version

## 12. Luồng người dùng chính

### Luồng 1: Tạo hồ sơ mới từ GCN

1. Tải file GCN
2. Xem file, xoay/crop nếu cần
3. Quét AI / OCR
4. Kiểm tra dữ liệu trích xuất
5. Đồng bộ vào form hồ sơ
6. Bổ sung thông tin nghiệp vụ
7. Lưu hồ sơ
8. Xuất Excel / Word / PDF nếu cần

### Luồng 2: Tra cứu và cập nhật hồ sơ

1. Vào Quản lý hồ sơ
2. Tìm kiếm / lọc
3. Mở popup sửa
4. Chỉnh sửa thông tin
5. Đổi trạng thái thanh toán nếu cần
6. Lưu

### Luồng 3: Xuất bộ hồ sơ phát hành

1. Chọn hồ sơ
2. Preview tài liệu
3. So sánh preview với file đã xuất
4. Xuất Word
5. Duyệt và xuất PDF
6. Đóng gói ZIP

### Luồng 4: Quản trị template

1. Chọn template
2. Kiểm tra placeholder
3. Chỉnh sửa nhanh nội dung
4. Gắn nhãn version
5. Khóa production
6. Restore nếu cần

### Luồng 5: Theo dõi doanh thu và công nợ

1. Vào Dashboard
2. Chọn năm / tháng / bộ lọc
3. Xem KPI
4. Xem biểu đồ
5. Xem bảng công nợ
6. Quay lại hồ sơ để đổi trạng thái hoặc xử lý tiếp

## 13. Kỳ vọng đầu ra từ công ty UI/UX

Đề nghị đơn vị UI/UX bàn giao:

1. User flow
2. Information architecture
3. Wireframe
4. UI mockup hoàn chỉnh
5. Design system cơ bản
6. Prototype tương tác cho các luồng chính
7. Trạng thái đầy đủ:
   - empty state
   - loading state
   - error state
   - success state
   - locked / disabled state
8. Quy chuẩn màu cho:
   - doanh thu
   - công nợ
   - đã thanh toán
   - chưa thanh toán
   - warning
   - production / draft / testing

## 14. Ghi chú quan trọng cho đội UI/UX

- Sản phẩm thiên về năng suất làm việc nội bộ, không phải app marketing.
- Cần ưu tiên hiệu quả vận hành hơn là trang trí.
- Cần dùng tiếng Việt có dấu đầy đủ.
- Cần thiết kế đủ linh hoạt để sau này tích hợp thêm:
  - Outlook / email
  - web nội bộ
  - báo cáo nâng cao
  - đăng nhập thật
  - audit log

## 15. Kết luận

Đây là một phần mềm nội bộ có độ phức tạp trung bình đến cao, gồm đồng thời:

- OCR / AI document intake
- form nghiệp vụ hành chính
- quản lý hồ sơ
- xuất tài liệu Word/PDF
- quản lý template
- dashboard doanh thu / công nợ

Do đó, UI/UX cần được tiếp cận như một **hệ thống tác nghiệp nội bộ chuyên sâu**, không phải một ứng dụng biểu mẫu đơn giản.
