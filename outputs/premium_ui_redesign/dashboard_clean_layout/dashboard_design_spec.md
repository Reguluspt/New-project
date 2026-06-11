# Tai lieu thiet ke - Tab Dashboard

Ngay chot: 06/06/2026  
Trang thai: Ban preview da duoc anh duyet ve bo cuc chinh

## Muc tieu

Tab `Dashboard` duoc thiet ke lai theo cung ngon ngu voi tab `Quan ly ho so`:

- Giao dien sach, sang, theo huong Fluent Design.
- Top navigation active chi dung underline xanh.
- Bieu do la vung phan tich chinh, co do rong co dinh.
- Bang bao cao nam ben phai va la vung co gian.
- Khong them chuc nang ngoai code Dashboard hien tai, chi them bieu do ty le ngan hang theo yeu cau.

## Thanh phan theo code hien tai

Dashboard gom:

- Bo loc: Nam thong ke.
- Bo loc: Nguon/ngan hang.
- Bo loc: Loai khach hang.
- Bo loc: Chuyen vien kinh doanh.
- Bo loc: Trang thai ho so.
- Chon thang theo doi.
- 4 KPI:
  - Doanh thu du kien ca nam.
  - Da thanh toan ca nam.
  - Cong no ton ca nam.
  - Doanh thu du kien trong thang.
- Bieu do Doanh thu vs Cong no hang thang.
- Bang Tong hop theo thang.
- Bang Bao cao cong no chi tiet.
- Doughnut chart ty le doanh thu theo ngan hang trong nam.

## Bo cuc da chot

1. Header
   - Tieu de: `Dashboard`.
   - Caption giai thich ngan.
   - Khong dat CTA lon trong header.

2. Filter bar
   - Mot hang 6 select:
     - Nam.
     - Nguon.
     - Loai KH.
     - CVKD.
     - Trang thai.
     - Thang.
   - Select dung nen trang, vien xam nhat, bo goc 9px.

3. KPI row
   - 4 KPI cung mot hang.
   - 3 KPI dau nen trang, vien xam nhat.
   - KPI doanh thu thang dung Fluent blue lam primary.
   - So lieu dung font weight lon, tabular numbers.
   - Thanh progress cho ty le thu nam.

4. Workspace
   - Chia 2 cot:
     - Cot trai: bieu do, do rong co dinh `760px`.
     - Cot phai: cac bang bao cao, dung `minmax(0, 1fr)` de co gian theo khung.
   - Chi cot phai co gian, cot bieu do khong bi co lai.

5. Cot trai - Chart stack
   - Panel 1: Bieu do cot `Doanh thu vs Cong no hang thang`.
   - Panel 2: Doughnut chart `Ty le doanh thu theo ngan hang`.
   - Hai panel xep doc.

6. Cot phai - Tables
   - Panel 1: `Tong hop theo thang`.
   - Panel 2: `Bao cao cong no chi tiet`.
   - Hai bang xep doc va co gian trong cot phai.

## Bieu do Doanh thu vs Cong no

- Dang bar chart nhom theo thang.
- Doanh thu: Fluent blue.
- Cong no: xanh nhat.
- Co legend tren goc phai panel.
- Khung chart co do rong co dinh theo cot trai, khong co theo bang.

## Doughnut chart theo ngan hang

Muc dich:

- The hien ty le doanh thu du kien trong nam theo he thong ngan hang.

Style da chot:

- Doughnut chart nam trong panel rieng ben duoi bieu do cot.
- Text o tam chart phai can giua chinh xac trong lo tron.
- Text trung tam:
  - Dong 1: tong doanh thu, vi du `3.284`.
  - Dong 2: don vi, vi du `Tong Tr`.
- Legend nam ben phai chart:
  - Mau.
  - Ten ngan hang.
  - Ty le phan tram.

Vi du data preview:

- VCB Gia Lai: 38%.
- BIDV Quy Nhon: 24%.
- Vietinbank Kon Tum: 18%.
- VCB Dak Lak: 11%.
- Khac: 9%.

## Bang bao cao

### Tong hop theo thang

Cot:

- Thang.
- Ho so.
- Du kien.
- Da thu.
- Cong no.

Style:

- Header can giua.
- So tien can phai, in dam.
- Duong chia cot xam nhat.
- Khong dung vach xanh.

### Bao cao cong no chi tiet

Cot:

- So HD.
- Khach hang.
- Ngan hang.
- Con lai.

Style:

- Header can giua.
- So tien can phai, in dam.
- Ten ngan hang dai duoc truncate neu cot hep.
- Bang nam trong panel co gian ben phai.

## Mau sac va interaction

- Nen app: trang, xam rat nhat.
- Accent chinh: Fluent blue `#0f6cbd` / brand blue `#0057d8`.
- Active nav: chi underline xanh, khong co nen xanh nhat hay khung pill.
- Panel: nen trang, vien xam nhat, bo goc 12px.
- Table header: xanh xam rat nhat.
- Khong dung shadow nang cho cac bang/bieu do.

## File lien quan

- Preview HTML: `dashboard_clean_preview.html`
- Preview PNG: `dashboard_clean_preview.png`

## Ghi chu de ap dung cho tab tiep theo

- Neu tab co vung data visualization, co the co dinh cot chinh va cho bang/phu tro co gian.
- Active state tiep tuc dung underline, tranh nut active co khung bao.
- Bang du lieu: header can giua, body uu tien can trai cho text va can phai cho so tien.
- Neu them chart moi, phai gan voi du lieu/thao tac thuc te cua tab, khong them chart trang tri.
