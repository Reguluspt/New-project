# Tai lieu thiet ke - Tab Chuyen phat

Ngay chot: 06/06/2026  
Trang thai: Ban preview da duoc anh duyet ve bo cuc chinh

## Muc tieu

Tab `Chuyen phat` duoc thiet ke lai theo huong danh ba nghiep vu gon, sach:

- Quan ly nguoi nhan phat hanh/chuyen phat.
- Giu cac chuc nang hien co trong code: xem danh sach, sua bang, luu thay doi.
- Them chuc nang tao danh ba moi theo yeu cau da duyet.
- Form tao/cap nhat nam o panel ben phai, bang danh sach nam ben trai.

## Thanh phan theo code hien tai

Tab gom:

- Danh sach nguoi nhan chuyen phat.
- Tao du lieu mau khi chua co du lieu.
- Bang editable voi cac cot:
  - ID.
  - Ten goi nho.
  - Thong tin chi tiet cot phai.
- Luu thay doi.
- Chuan hoa thong tin nguoi nhan de dung trong email phat hanh.

## Bo cuc da chot

1. Header
   - Tieu de: `Danh ba chuyen phat`.
   - Caption ngan ve nguoi nhan, dia chi, dien thoai va noi dung cot phai.
   - Active nav chi dung underline xanh.

2. KPI row
   - Tong lien he.
   - Lien he day du.
   - Dang cap nhat.
   - Ban nhap moi.

3. Workspace
   - Ben trai: bang danh ba chuyen phat.
   - Ben phai: panel `Tao danh ba moi`.
   - Toolbar tren bang co nut `Tao danh ba moi`.

4. Bang danh ba
   - Header can giua.
   - Body can trai.
   - Dong dang chon co nen xanh rat nhe va dai xanh ben trai.
   - Khong dung vach xanh doc.

## Bang danh sach

Cot chinh:

- `ID`.
- `Ten goi nho`.
- `Thong tin chi tiet`.
- `Trang thai`.

Trong `Thong tin chi tiet` uu tien hien:

- Ten don vi/nguoi nhan.
- Dia chi.
- Dien thoai.
- Ghi chu phat hanh neu co.

Trang thai:

- `Day du`.
- `Can bo sung`.
- `Nhap`.

## Panel Tao danh ba moi

Panel ben phai gom:

- Ten goi nho.
- Don vi/nguoi nhan.
- Dia chi.
- Dien thoai.
- Email neu co.
- Noi dung cot phai / ghi chu.

Action:

- `Tao moi` la primary.
- `Luu thay doi`.
- `Xoa dong`.
- `Lam moi`.

Style:

- Field nen xam rat nhat, label small caps.
- Button primary dung Fluent blue.
- Button thuong nen trang, vien xam nhat.
- Button xoa dung red-soft.

## Yeu cau da chot bo sung

- Co chuc nang `Tao danh ba moi`.
- Nut nay nam dung ngu canh trong tab Chuyen phat.
- Khong dua cac nut dong bo Telegram/Mail vao tab nay.

## Mau sac va interaction

- Nen chinh trang/xam rat nhat.
- Accent Fluent blue.
- Trang thai day du dung xanh la nhe.
- Trang thai can bo sung dung cam nhe.
- Panel va bang deu dung border hairline, bo goc 12px.

## File lien quan

- Preview HTML: `delivery_clean_preview.html`
- Preview PNG: `delivery_clean_preview.png`

## Ghi chu de trien khai

- Neu tiep tuc dung `st.data_editor`, can canh lai chieu cao bang de nut luu khong bi day khoi viewport.
- Form tao moi nen tach khoi bang editable de tranh nguoi dung nhap nham vao dong dang co.
