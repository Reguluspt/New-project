# Tai lieu thiet ke - Tab Nhap ho so

Ngay chot: 06/06/2026  
Trang thai: Ban preview da duoc anh duyet ve bo cuc chinh

## Muc tieu

Tab `Nhap ho so` duoc thiet ke lai theo cung ngon ngu voi `Dashboard` va `Quan ly ho so`:

- Giao dien sach, sang, theo huong Fluent Design.
- Tap trung vao workflow: tai file, quet AI, xem tai lieu, kiem tra form, luu/xuat/gui.
- Giu chuc nang hien co trong code, khong them luong moi.
- Cac khu vuc co do rong ro rang, tranh bi co/gian gay vo form.

## Thanh phan theo code hien tai

Tab gom:

- File uploader: PDF, PNG, JPG, JPEG, WEBP, nhieu file.
- Hang doi file da tai len.
- Nut quet file bang AI provider hien tai.
- Ket qua AI tu dua vao form.
- Viewer tai lieu dau vao:
  - Thumbnail trang.
  - Che do xem PDF.
  - Xoay trai/phai.
  - Zoom.
  - Vung preview trang.
- Form nhap ho so:
  - Tab `Khach hang Ca nhan`.
  - Tab `Khach hang To chuc`.
  - Thong tin khach hang.
  - Thong tin nghiep vu.
  - Thong tin GCN trich xuat tu AI.
  - Ho so gan nhat.
- Action:
  - Luu ho so vao SQLite.
  - Xuat Excel.
  - Gui mail yeu cau dinh gia.
  - Gui yeu cau len Web.

## Bo cuc da chot

1. Header
   - Tieu de: `Nhap ho so`.
   - Caption ngan: tai GCN, quet AI, kiem tra form va luu/xuat/gui yeu cau dinh gia.
   - Active nav chi dung underline xanh, khong co khung/pill.

2. Intake bar
   - Nam ngay duoi header.
   - Gom 3 cum:
     - Upload file.
     - Hang doi file + nut quet AI.
     - Tom tat ket qua AI.
   - Cac cum dung nen xam rat nhat, vien hairline, bo goc 12px.

3. Workspace
   - Chia 2 cot:
     - Ben trai: viewer tai lieu, co gian theo khung.
     - Ben phai: form nhap ho so, co dinh `780px`.
   - Ly do: form nhap lieu can width on dinh de cac field khong bi thay doi bo cuc.

4. Viewer tai lieu
   - Panel ben trai.
   - Grid rows phai la `auto auto 1fr`:
     - Header.
     - Toolbar.
     - Vung tai lieu.
   - Khong de toolbar bi keo gian tao khoang trang.
   - Thumbnail nam cot trai trong viewer.
   - Trang preview nam ben phai.
   - Vung AI nhan dien hien trong preview tai lieu.

5. Form nhap ho so
   - Do rong co dinh `780px`.
   - Co scroll noi bo cho noi dung form.
   - Action bar nam co dinh duoi panel.
   - Section trong form dung `flex: 0 0 auto` de khong bi co lai va cat noi dung.

## Form section da chot

### Thong tin khach hang

Hien cac truong chinh:

- So hop dong.
- Ngay hop dong.
- Ten khach hang.
- Dia chi.
- CCCD/CMND.

### Thong tin nghiep vu

Hien cac truong chinh:

- Tai san tham dinh gia.
- Loai tai san.
- So bo.
- Muc dich.
- Chi nhanh.
- Van phong.
- Nguon/doi tac.
- Phi tham dinh.
- Chuyen vien.
- Ghi chu ca nhan.

### Thong tin GCN trich xuat tu AI

- Mac dinh thu gon, tuong ung voi expander trong code goc.
- Khong hien grid chi tiet trong preview mac dinh.
- Chi hien header va trang thai `Dang thu gon`.

### Ho so gan nhat

- Nam trong form body, phia duoi cac section chinh.
- Bang compact.
- Header can giua.

## Action bar

Nam co dinh duoi form panel.

Nut:

- `Luu SQLite`
- `Xuat Excel` - primary Fluent blue.
- `Gui mail`
- `Gui Web`

Style:

- Nền trắng, viền xám nhạt.
- Primary dùng Fluent blue.
- Không dùng icon/emoji nếu không cần.
- Không để action bị khuất khi form scroll.

## Mau sac va interaction

- Nen app: trang va xam rat nhat.
- Accent: Fluent blue / brand blue.
- Active nav/tab: underline xanh.
- Panel: vien hairline, bo goc 12px.
- Status:
  - Applied/da quet: xanh la nhe.
  - Pending/chua luu: cam nhe.
- Field:
  - Nen xam rat nhat.
  - Label small caps.
  - Gia tri in dam.

## Cac loi da sua

- Viewer bi khoang trang lon:
  - Nguyen nhan: viewer co 3 phan nhung grid chi khai bao 2 rows.
  - Sua: `grid-template-rows: auto auto 1fr`.

- Form section bi khuất/cat noi dung:
  - Nguyen nhan: form body flex scroll nhung section bi co lai.
  - Sua: section dung `flex: 0 0 auto`.

- Cum form bi co/gian:
  - Sua: workspace dung `grid-template-columns: minmax(0, 1fr) 780px`.
  - Viewer ben trai co gian, form ben phai co dinh.

## File lien quan

- Preview HTML: `entry_clean_preview.html`
- Preview PNG: `entry_clean_preview.png`

## Ghi chu de ap dung cho tab tiep theo

- Neu tab co form nhap lieu dai, nen co dinh width form de field khong nhay layout.
- Neu co viewer/preview, cho viewer la phan co gian.
- Cac expander mac dinh dong trong code goc nen preview o trang thai thu gon, khong mo het lam roi UI.
- Action quan trong nen co dock/co dinh, tranh bi day khoi viewport khi noi dung cuon.
