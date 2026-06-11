# Tai lieu thiet ke - Tab So Bo

Ngay chot: 06/06/2026  
Trang thai: Ban preview da duoc anh duyet ve bo cuc chinh

## Muc tieu

Tab `So Bo` duoc thiet ke lai de giam roi khi theo doi nhieu yeu cau tu Telegram/Mail:

- Hien ro yeu cau dang cho phan hoi, da phan hoi va qua han.
- Giu dung cac chuc nang trong code: tim kiem, loc trang thai, dong bo Telegram, kiem tra Mail, mo ban do, tai GCN, xoa.
- Khong co tab phu trong noi dung vi top navigation da co `So Bo` active.
- Dua chi tiet yeu cau dang chon sang panel ben phai.

## Thanh phan theo code hien tai

Tab gom:

- Header `Giam sat yeu cau So bo`.
- Tim kiem nhanh.
- Loc trang thai: `Tat ca`, `Cho phan hoi`, `Da phan hoi`.
- Nut `Dong bo Telegram`.
- Nut `Kiem tra Mail ngay`.
- KPI:
  - Cho phan hoi.
  - Da phan hoi.
  - Thoi gian phan hoi trung binh.
- Danh sach yeu cau.
- Mo ban do.
- Tai GCN.
- Xoa yeu cau neu khong phai tai khoan guest.

## Bo cuc da chot

1. Header
   - Tieu de: `Giam sat yeu cau So bo`.
   - Caption ngan ve theo doi phan hoi tu Telegram bot va hop thu nghiep vu.
   - Ben phai hien trang thai dong bo gan nhat.
   - Khong co hang tab phu ben duoi header.

2. KPI row
   - Tong yeu cau.
   - Cho phan hoi.
   - Da phan hoi.
   - Thoi gian phan hoi TB.

3. Workspace
   - Ben trai: danh sach chi tiet yeu cau.
   - Ben phai: panel chi tiet yeu cau dang chon.

4. Toolbar danh sach
   - Search input.
   - Select trang thai.
   - `Telegram` primary.
   - `Kiem tra Mail` secondary.

## Danh sach yeu cau

Cot chinh:

- `Ma / ngay gui`.
- `Tieu de & tai san`.
- `Nguon / nguoi nhan`.
- `Trang thai`.
- `Thao tac`.

Style:

- Header can giua.
- Body can trai cho text dai.
- Trang thai can giua bang pill xep doc.
- Dong dang chon co nen xanh rat nhe va dai xanh ben trai.
- Bang/row dung grid xam nhat, khong dung vach xanh doc.

## Trang thai va timer

Pill:

- `Cho phan hoi`: cam nhe.
- `Da phan hoi`: xanh la nhe.
- `Tre`: do nhe.
- Thoi gian: xanh duong nhe.

Noi dung timer theo logic code:

- Pending duoi nguong: `4g`, `12g`.
- Pending qua han: `Tre: 2 ngay 3g`.
- Responded: `6g`, `8g`.

## Thao tac tren dong

Dung icon button Fluent:

- Mo ban do.
- Tai GCN.
- Xoa, neu co quyen.

Style:

- Nut ban do primary blue.
- Tai GCN nen trang, vien xam nhat.
- Xoa red-soft.
- Khong chen text dai vao bang de tranh tran cot.

## Panel chi tiet ben phai

Gom:

- Ma yeu cau va trang thai.
- Thong tin gui:
  - Ngay gui.
  - Nguon.
  - Nguoi nhan.
  - Thoi gian.
- Tai san:
  - Loai tai san.
  - Thua/to hoac thiet bi.
  - Dia chi.
- Ban do preview.
- Phan hoi mail:
  - Neu chua co: thong bao he thong se cap nhat khi mailbox co email tra loi.
  - Neu co: hien noi dung phan hoi.
- Action dock duoi panel:
  - `Mo ban do`.
  - `Tai GCN`.

## Loi da sua trong preview

- Hang tab phu trong noi dung bi du, da xoa.
- Danh sach bi cat dong cuoi do chieu cao khung, da sua grid panel de bang tinh chieu cao dung.
- Panel chi tiet ben phai duoc thu gon nhip doc de khong cat phan phan hoi mail.

## File lien quan

- Preview HTML: `sobo_clean_preview.html`
- Preview PNG: `sobo_clean_preview.png`

## Ghi chu de trien khai

- Neu app that co nhieu dong, danh sach nen scroll noi bo thay vi day panel phai.
- Khong them nut tao moi vao tab nay, vi code tab nay la monitoring/sync.
- Khu vuc xoa can co confirm nhu code hien tai.
