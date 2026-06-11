# Tai lieu thiet ke - Tab To Chuc

Ngay chot: 06/06/2026  
Trang thai: Ban preview da duoc anh duyet ve bo cuc chinh

## Muc tieu

Tab `To Chuc` duoc thiet ke lai theo cung ngon ngu voi cac tab da chot:

- Quan ly danh ba to chuc/tai khoan doanh nghiep ro rang.
- Giu lai cac chuc nang trong code hien tai: xem danh sach, them, cap nhat, xoa, trich xuat tu hop dong bang AI.
- Dua form them/cap nhat sang panel ben phai de danh sach ben trai van la trung tam.
- Giam cam giac form dai bang cac truong co nhom va trang thai ro.

## Thanh phan theo code hien tai

Tab gom:

- Bang danh sach to chuc.
- Tao du lieu mau khi chua co du lieu.
- Form them moi to chuc.
- Form cap nhat to chuc.
- Xoa to chuc.
- Khu vuc trich xuat hang loat bang AI tu hop dong.
- Luu tat ca ket qua AI vao danh ba.

## Bo cuc da chot

1. Header
   - Tieu de: `Danh ba to chuc`.
   - Caption ngan ve quan ly MST, dia chi, dai dien va chuc vu.
   - Active nav tren topbar chi dung underline xanh.

2. KPI row
   - Tong to chuc.
   - Da co MST.
   - Da co nguoi dai dien.
   - Ket qua AI cho duyet.

3. Workspace
   - Ben trai: danh sach to chuc.
   - Ben phai: panel `Them / cap nhat to chuc`.
   - Duoi danh sach: khu vuc AI import tu hop dong.

4. Danh sach to chuc
   - Dung bang ro cot, khong dung card lap lai qua day.
   - Header can giua.
   - Body can trai cho text dai.
   - Dong dang chon co nen xanh rat nhe va dai xanh ben trai.

## Bang danh sach

Cot chinh:

- `ID`.
- `Ma so thue`.
- `Ten cong ty`.
- `Ten viet tat`.
- `Dia chi`.
- `Nguoi dai dien`.
- `Chuc vu`.

Style:

- Duong chia cot xam nhat.
- Khong dung vach xanh doc.
- Text dai duoc cat gon hop ly.
- MST/ID dung tabular numbers.

## Panel them / cap nhat

Panel ben phai gom:

- Trang thai dang sua / tao moi.
- Truong MST.
- Ten cong ty bat buoc.
- Ten viet tat.
- Dia chi.
- Nguoi dai dien.
- Chuc vu.
- Action:
  - `Them moi`.
  - `Cap nhat`.
  - `Xoa`.
  - `Lam moi`.

Style:

- Field nen xam rat nhat, vien hairline.
- Label small caps.
- Nut primary dung Fluent blue.
- Nut xoa dung red-soft, khong qua gay gat.

## Khu vuc AI import

Muc dich:

- Hien luong `Trich xuat hang loat bang AI`.
- Cho phep xem cac ket qua dang cho duyet.
- Luu tat ca vao danh ba.

Bo cuc:

- Nam duoi bang chinh.
- Dung panel rieng, khong chen vao bang.
- Ket qua AI hien dang compact row/card.
- Co trang thai: `Cho duyet`, `San sang luu`.

## Mau sac va interaction

- Nen app: trang va xam rat nhat.
- Accent: Fluent blue `#0f6cbd` / brand blue `#0057d8`.
- Trang thai OK: xanh la nhe.
- Canh bao/thieu du lieu: cam nhe.
- Active state: underline xanh, khong pill/khung boc.

## File lien quan

- Preview HTML: `organizations_clean_preview.html`
- Preview PNG: `organizations_clean_preview.png`

## Ghi chu de trien khai

- Khong dua action xoa vao vi tri qua gan nut luu chinh neu co the gay bam nham.
- Khi bang rong, empty state phai co CTA tao du lieu mau theo code hien tai.
- AI import nen la section rieng de tranh lam roi form them/cap nhat.
