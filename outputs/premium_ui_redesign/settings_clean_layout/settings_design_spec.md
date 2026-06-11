# Tai lieu thiet ke - Tab Cai dat

Ngay chot: 06/06/2026  
Trang thai: Ban preview da duoc tao theo code hien tai

## Muc tieu

Tab `Cai dat` duoc thiet ke lai theo huong ro nhom, de quan tri he thong ma khong bi roi:

- Tach cac nhom cau hinh thanh navigation ben trai.
- Vung giua tap trung vao nhom dang chon.
- Vung phai hien suc khoe he thong, OAuth2 va quan tri du lieu dang tom tat.
- Giu dung cac chuc nang trong code hien tai, khong them luong moi.

## Thanh phan theo code hien tai

Tab gom 4 nhom:

1. `Cau hinh Template`
   - File mau Excel.
   - Thu muc mau Word ca nhan.
   - Thu muc mau Word to chuc.
   - Ten nguoi chinh sua template.
   - Trang thai duong dan.
   - Quan ly danh sach chon trong Form Excel.

2. `Suc khoe he thong`
   - Kiem tra SQLite.
   - Kiem tra thu muc template.
   - Kiem tra LibreOffice/PDF.
   - Kiem tra Gemini API key.
   - Sao luu du lieu nhanh.

3. `Quan tri du lieu`
   - Sao luu.
   - Khoi phuc.
   - Xoa trang.

4. `Tich hop OAuth2`
   - Redirect URI.
   - Google Workspace/Gmail API.
   - Microsoft Outlook/Graph API.
   - Outlook SMTP alias.
   - Mail So bo.

## Bo cuc da chot

1. Header
   - Tieu de: `Cai dat he thong`.
   - Caption ngan ve template, danh sach chon Excel, sao luu va OAuth2.
   - Active nav tren topbar chi dung underline xanh.

2. KPI row
   - Nhom cau hinh.
   - Template Word.
   - SQLite.
   - OAuth2.

3. Workspace 3 cot
   - Cot trai: navigation nhom cau hinh.
   - Cot giua: form cau hinh nhom dang chon.
   - Cot phai: tom tat suc khoe, OAuth2, quan tri du lieu.

## Navigation ben trai

Danh sach:

- `Cau hinh Template`.
- `Suc khoe he thong`.
- `Quan tri du lieu`.
- `Tich hop OAuth2`.

Style:

- Item active dung nen xanh rat nhe va dai xanh ben trai.
- Moi item co icon nho, label dam, caption ngan.
- Khong dung tab ngang trong noi dung de tranh day giao dien.

## Vung giua - Cau hinh Template

Gom:

- File mau Excel.
- Thu muc mau Word ca nhan.
- Thu muc mau Word to chuc.
- Nguoi chinh sua template.
- Trang thai duong dan.
- 3 status card:
  - Form Excel.
  - Mau ca nhan.
  - Mau to chuc.
- Quan ly danh sach chon trong Form Excel:
  - Cot trai: nhom danh sach.
  - Cot phai: gia tri danh sach, moi dong mot gia tri.

Action dock duoi:

- `Kiem tra duong dan`.
- `Luu danh sach chon`.
- `Luu cau hinh template` la primary.

## Vung phai

### Suc khoe he thong

Hien compact:

- Co so du lieu.
- LibreOffice PDF.
- Gemini API.

Trang thai:

- OK: pill xanh.
- Thieu/can cau hinh: pill cam.
- Loi: pill do.

### Tich hop OAuth2

Hien compact:

- Google Gmail API.
- Outlook Graph API.
- Redirect URI.
- Mail So bo.

Trang thai chua lien ket dung red-soft, khong gay gat.

### Quan tri du lieu

Gom:

- Tao ban sao luu moi.
- Khoi phuc tu file ZIP.
- Xoa toan bo du lieu.
- Ghi chu danger zone yeu cau nhap `XAC NHAN XOA`.

## Mau sac va interaction

- Nen chinh trang/xam rat nhat.
- Accent Fluent blue.
- Danger zone dung do nhat, khong dung nen do dam.
- Field dung nen xam rat nhat, vien hairline, label small caps.
- Button primary dung Fluent blue.
- Button danger dung red-soft.

## File lien quan

- Preview HTML: `settings_clean_preview.html`
- Preview PNG: `settings_clean_preview.png`

## Ghi chu de trien khai

- Vi tab Cai dat co nhieu noi dung, nen uu tien navigation doc ben trai thay cho nhieu tab ngang.
- Nhung thao tac nguy hiem can giu confirm text nhu code hien tai.
- Khong hien API secret dang raw trong preview/implementation, chi dung password input hoac masked value.
