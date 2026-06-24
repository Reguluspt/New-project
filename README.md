# Hệ Thống Thẩm Định Giá — Flask + React SPA

Hệ thống quản lý hồ sơ thẩm định giá, chuyển đổi từ Streamlit sang kiến trúc **Flask REST API + React SPA** hiện đại.

---

## Kiến Trúc

```
┌─────────────────────────────────────────────────────────┐
│                    React SPA (web/)                     │
│   Vite + React 18 + Ant Design + React Query           │
│   http://localhost:5173 (dev) / /  (production)        │
└───────────────────┬─────────────────────────────────────┘
                    │  /api/*
┌───────────────────▼─────────────────────────────────────┐
│               Flask API (api/)                          │
│   Python + Flask Blueprints                             │
│   http://localhost:5000                                 │
└───────────────────┬─────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────┐
│               Data Layer (src/)                         │
│   sqlite_store.py · database_manager.py                │
│   document_exporter.py · mail_service.py               │
│   gemini_extractor.py · telegram_bot · ...             │
└─────────────────────────────────────────────────────────┘
```

---

## Cài Đặt (Lần Đầu)

### Yêu Cầu

| Phần mềm | Phiên bản |
|----------|-----------|
| Python   | ≥ 3.11    |
| Node.js  | ≥ 18      |
| npm      | ≥ 9       |

### Các Bước

```bat
# 1. Cài đặt toàn bộ
CaiDat.bat

# 2. Cấu hình API keys (Gemini, Telegram, OAuth, ...)
# Sửa file API.env với thông tin của bạn

# 3. Build giao diện React (lần đầu, hoặc khi có thay đổi frontend)
build_production.bat
```

---

## Chạy Ứng Dụng

### Development (khuyến nghị khi phát triển)

```powershell
# Terminal 1: Flask API
.venv\Scripts\python.exe -m api.run --debug

# Terminal 2: React dev server (hot-reload)
cd web
npm run dev
```

Frontend: http://localhost:5173 → proxy đến Flask API tại :5000

### Production

```bat
# Bước 1: Build React
build_production.bat

# Bước 2: Khởi động hệ thống
KhoiDongHeThong.bat
```

Flask phục vụ cả API (`/api/*`) và React static files (`/`) trên port 5000.

---

## Endpoints API

| Nhóm | Prefix | Chức năng |
|------|--------|-----------|
| Auth | `/api/auth/` | Đăng nhập, đăng xuất, thông tin user |
| Dashboard | `/api/dashboard/` | KPI, thống kê, bộ lọc |
| Hồ sơ | `/api/cases/` | CRUD hồ sơ thẩm định |
| Văn bản | `/api/cases/:id/documents/` | Tạo, preview, download, email |
| Nhập hồ sơ | `/api/entry/` | Upload file, OCR, lưu |
| Sơ bộ | `/api/sobo/` | Yêu cầu thẩm định sơ bộ |
| Tổ chức | `/api/organizations/` | CRUD tổ chức |
| Chuyển phát | `/api/delivery/contacts/` | Danh bạ chuyển phát |
| Templates | `/api/templates/` | Quản lý mẫu Word |
| Cài đặt | `/api/settings/` | Cấu hình hệ thống, backup, OAuth |

---

## Testing

```powershell
# Chạy toàn bộ bộ test (39 integration tests)
.venv\Scripts\python.exe -m pytest tests/test_api/ -v

# Chạy một module cụ thể
.venv\Scripts\python.exe -m pytest tests/test_api/test_cases.py -v
```

---

## Docker Deployment

```bash
# Build và chạy toàn bộ stack
docker-compose up --build

# Chỉ API
docker build -f Dockerfile.api -t thamdinh-api .
docker run -p 5000:5000 --env-file API.env thamdinh-api

# Web (Nginx + React)
docker build -f web/Dockerfile.web -t thamdinh-web ./web
docker run -p 80:80 thamdinh-web
```

---

## Cấu Trúc Dự Án

```
New project/
├── api/                    # Flask REST API
│   ├── __init__.py         # App factory
│   ├── run.py              # Entry point
│   ├── config.py           # Configuration
│   └── blueprints/         # Route handlers
│       ├── auth.py
│       ├── dashboard.py
│       ├── cases.py
│       ├── documents.py
│       ├── entry.py
│       ├── sobo.py
│       ├── organizations.py
│       ├── delivery.py
│       ├── templates_bp.py
│       └── settings_bp.py
├── web/                    # React SPA
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── hooks/
│   │   └── styles/
│   ├── Dockerfile.web
│   └── nginx.conf
├── src/                    # Core business logic (không sửa đổi)
├── tests/
│   └── test_api/           # Integration tests
├── data/                   # SQLite databases
├── samples/                # Template files
├── Dockerfile.api
├── docker-compose.yml
├── build_production.bat    # Build React cho production
├── KhoiDongHeThong.bat     # Khởi động hệ thống
├── CaiDat.bat              # Cài đặt lần đầu
└── requirements.txt
```

---

## Tài Khoản Mặc Định

| Loại | Username | Mật khẩu |
|------|----------|-----------|
| Admin | `truongpnt` | *(xem API.env)* |

> **Lưu ý bảo mật**: Đổi mật khẩu mặc định trước khi deploy production. Cấu hình trong `API.env`.
