# Tu dong hoa ho so tham dinh

MVP nay tap trung vao Buoc 1: doc PDF/anh Giay chung nhan quyen su dung dat bang AI online, cho nguoi dung kiem tra lai, sau do luu vao SQLite va xuat du lieu vao mau Excel `Form nhap lieu.xlsx`.

## Chuc nang hien co

- Upload PDF hoac anh GCN.
- Goi Gemini API hoac OpenAI Responses API de trich xuat:
  - So thua dat.
  - So to ban do.
  - Dia chi thua dat.
  - Ten chu so huu cuoi cung.
  - Dia chi chu so huu cuoi cung.
  - So CCCD/CMND cua chu so huu cuoi cung.
- Hien do tin cay va bang chung ngan de kiem tra.
- Cho sua tay truoc khi xuat.
- Ghi vao sheet `Up Hs` cua file mau Excel.
- Luu ho so vao SQLite, mac dinh la `data/cases.db`.
- Tim kiem, sua va xoa ho so da luu.
- Import du lieu cu tu file Excel `Database.xlsx` vao SQLite.
- Luu PDF/anh GCN goc vao thu muc rieng cua tung ho so.
- Xuat bo ho so ca nhan tu SQLite: Hop dong, Phieu yeu cau, Bien ban nghiem thu.
- Xuat bo ho so to chuc tu SQLite: Hop dong, Bien ban nghiem thu/thanh ly, De nghi thanh toan, Thu chao phi.
- Xem truoc noi dung Word da render truoc khi xuat file that.
- So sanh noi dung preview voi file Word da xuat de duyet lan cuoi.
- Sau khi duyet, app co the xuat tu dong ca bo PDF tu cac file Word.
- Co the dong goi ZIP ho so gom file goc, Word va PDF de gui noi bo/luu tru.
- Mau Word da duoc chuan hoa sang placeholder `{{...}}`.
- Co man hinh "Quan ly template" de sua duong dan template, xem placeholder, va bao loi thieu placeholder bat buoc.
- Co placeholder editor ngay trong app de sua nhanh tung doan template co placeholder.
- Co lich su chinh sua template de biet ai sua doan nao va luc nao.
- Co khoa template production de chan sua nham mau dang dung that.
- Co snapshot version va khoi phuc template truc tiep tu lich su.
- Co nhan phien ban template `production`, `draft`, `testing`.
- Co phan quyen local theo role cho sua template, restore template, va duyet PDF.

## Cai dat

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Mo file `.env` va dien `OPENAI_API_KEY`.
Neu dung Gemini, dien `GEMINI_API_KEY`. Mac dinh app chon model `gemini-2.5-flash`.

## Chay phan mem

```powershell
.\.venv\Scripts\streamlit.exe run app.py
```

Sau do mo dia chi Streamlit hien trong terminal, thuong la `http://localhost:8501`.

## Luu y bao mat

Khi bam quet AI, file GCN se duoc gui den nha cung cap AI da chon trong sidebar de xu ly hinh anh/PDF. Chi upload ho so khi cong ty cho phep dung AI online cho du lieu khach hang. Neu can che do noi bo/offline, can thay module `src/extractor.py`/`src/gemini_extractor.py` bang OCR local va model local.

## SQLite database

SQLite la database chinh cua phan mem, nam mac dinh tai `data/cases.db`. Sidebar co nut "Import Excel vao SQLite" de chuyen du lieu cu tu `Database.xlsx`.

Man hinh "Quan ly ho so" ho tro:

- Tim theo ten khach hang, so hop dong, CCCD, dia chi, tai san, ngan hang hoac ghi chu.
- Chon mot ho so de sua.
- Xoa ho so voi checkbox xac nhan.
- Xem truoc noi dung bo Word truoc khi xuat.
- So sanh preview voi file Word da xuat.
- Xuat bo Word cho khach hang ca nhan va to chuc.

## Thu muc ho so

Khi luu ho so moi, app tao thu muc theo dang `data/case_files/<ID>_<So hop dong>/`.

- File GCN goc nam trong `originals/`.
- Bo Word xuat ra nam trong `documents/`.
- Mau Word ca nhan nam mac dinh tai `samples/templates/individual/`.
- Mau Word to chuc nam mac dinh tai `samples/templates/organization/`.
- Danh sach placeholder: `docs/word_placeholders.md`.
- Cac mau can ghep muc dich + nguon nay dung `{{MUC_DICH_THAM_DINH_DAY_DU}}`.

Hai mau doanh nghiep goc dang o dinh dang `.doc` cu da duoc chuyen sang `.docx` trong thu muc `samples/templates/organization/` de app co the tu dong dien du lieu.

Mapping import tu Excel database cu:

- A: STT.
- B: Khach hang.
- C: Dia chi.
- D: Tai san tham dinh.
- E: Muc dich tham dinh.
- F: Phi tham dinh.
- G: So tien bang chu.
- H: Ghi chu ca nhan.
- I: Dien giai/So hop dong.
- J: Ngan hang/Nguon.
