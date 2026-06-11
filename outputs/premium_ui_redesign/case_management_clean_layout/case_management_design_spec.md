# Tai lieu thiet ke - Tab Quan ly ho so

Ngay chot: 06/06/2026  
Trang thai: Ban preview da duoc anh duyet ve bo cuc chinh

## Muc tieu

Tab `Quan ly ho so` duoc thiet ke lai theo huong sach, hien dai, gan voi Fluent Design:

- Bang ho so la trung tam.
- Hanh dong chi tiet chuyen sang panel ben phai.
- Giam so cot bang cach gop thong tin lien quan.
- Giu lai cac chuc nang hien co, khong them CTA sai ngu canh.
- Giao dien uu tien scan nhanh, ro trang thai, de thao tac tren ho so dang chon.

## Cau truc man hinh

1. Top navigation
   - Active nav chi dung chu dam va dai xanh ben duoi.
   - Khong dung nen xanh nhat, khong boc khung/pill cho nav active.

2. Page header
   - Tieu de: `Quan ly ho so`.
   - Mo ta ngan ve bo cuc.
   - Khong co nut `Tao ho so moi`.
   - Khong co nut `Dong bo Telegram/Mail` tren command bar cua tab nay.

3. Tabs noi bo
   - `Danh muc ho so`
   - `Doanh thu & Cong no`
   - Tab active chi co underline xanh, khong co khung bao.

4. Command bar
   - Tim kiem dong.
   - Tim trong ghi chu ca nhan.
   - Bo loc tom tat.
   - Nut `Xuat Excel`.

5. Workspace chinh
   - Ben trai: bang danh muc ho so.
   - Ben phai: panel chi tiet ho so dang chon.

6. Khu vuc duoi
   - Batch action.
   - Xuat Excel.
   - Ho so tu Telegram / Mail Listener, chi hien thi theo doi du lieu, khong dat CTA dong bo len command bar.

## Bang danh muc ho so

### Cot da chot

1. `Ho so`
   - Dong 1: So hop dong, vi du `N04-1055-DN`.
   - Dong 2: Ma tai san `TS1: 218034`, mau do.
   - Dong 3: `#ID | ngay`, vi du `#44 | 06/06/2026`.
   - Khong hien thi nguon ngan hang tai cot nay.

2. `Khach hang`
   - Ten khach hang.
   - Dia chi ngan.
   - CCCD voi ca nhan hoac MST voi to chuc.
   - Loai khach hang: `Ca nhan` / `To chuc`.

3. `Ghi chu`
   - Hien thi ghi chu ngan de scan nhanh.

4. `Tai san`
   - Ten tai san chinh.
   - Co the them dong phu neu can.

5. `Phi`
   - Gia tri tien, in dam.

6. `Trang thai`
   - Gop 2 thong tin:
     - Trang thai thanh toan.
     - Trang thai ho so.
   - Hien thi bang 2 pill xep doc.

### Style bang

- Header cot can giua.
- Body giu can trai cho du lieu dai, rieng cac cot ngan duoc can giua khi phu hop.
- Khong dung vach xanh giua cac cot.
- Duong chia cot dung xam nhat.
- Dong dang chon:
  - Nen xanh rat nhe.
  - Chi co mot dai xanh o mep trai dong.

## Panel chi tiet ben phai

Panel hien ho so dang chon, gom:

- Ma ho so va trang thai.
- Thong tin chinh.
- Tai san & file.
- Ghi chu.
- Cum action icon-only.

### Cum action icon-only

Da chot theo huong Fluent toolbar:

- 8 icon, 2 hang, 4 cot.
- Khong hien text trong nut.
- Moi nut co `title` de hover xem ten chuc nang.
- Nut chinh co nen Fluent blue.
- Nut thuong phang, khong khung nang.
- Nut xoa mau do nhe.
- Dung SVG line icon thay cho emoji/ky tu mau.

Danh sach action:

- Xem / Xuat.
- Sua ho so.
- Gui mail.
- Gui Web.
- Phat hanh.
- Xuat nhanh.
- Doi thanh toan.
- Xoa.

## Mau sac va cam giac

- Chu dao: trang, xam rat nhat, Fluent blue.
- Trang thai:
  - Thanh toan xong: xanh la nhe.
  - Chua thanh toan / cho thu: cam nhe.
  - Dang xu ly: xanh duong nhe.
  - Hoan thanh: xanh la nhe.
- Khong dung palette qua toi, qua nang, hoac khung the day dac.

## File lien quan

- Preview HTML: `case_management_clean_preview.html`
- Preview PNG: `case_management_clean_preview.png`

## Ghi chu de ap dung cho tab tiep theo

- Uu tien giam nhieu action trong bang, dua action theo object dang chon sang panel hoac toolbar.
- Active state chi nen dung underline/dai xanh, han che nen xanh nhat boc khung.
- Button icon nen theo Fluent: phang, vi tri ro, hover moi hien nen.
- Bang du lieu can giu du cot quan trong, nhung co the gop cot neu thong tin cung mot ngu canh.
