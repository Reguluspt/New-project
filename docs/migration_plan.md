# Kế hoạch chuyển đổi: Streamlit → Flask + React (Vite) SPA

> [!IMPORTANT]
> **Phương án B**: Flask REST API backend + React (Vite) SPA frontend
> **Ước lượng tổng**: 35-45 ngày developer | 10 phases
> **Stack**: Python Flask + SQLite | React 18 + Vite + Ant Design + TanStack Query

---

## Tổng quan kiến trúc mới

```
┌─────────────────────────────────────┐
│         React SPA (Vite)            │
│  Ant Design + TanStack Query        │
│  Port 5173 (dev) / nginx (prod)     │
└──────────────┬──────────────────────┘
               │ REST API (JSON)
               ▼
┌─────────────────────────────────────┐
│        Flask API Server             │
│  Flask-Login + JWT + Blueprints     │
│  Port 5000                          │
├─────────────────────────────────────┤
│  src/ modules (GIỮA NGUYÊN)        │
│  sqlite_store ← cases.db           │
│  database_manager ← telegram.db    │
│  document_exporter, email_utils...  │
└─────────────────────────────────────┘
       │              │            │
  Telegram Bot   Mail Listener   Ngrok
  (FastAPI:8000)  (IMAP daemon)  (tunnel)
```

---

## Chọn thư viện

| Vai trò | Thư viện | Lý do |
|---------|---------|-------|
| UI Framework | **Ant Design 5** | Enterprise-grade, có sẵn Table, Form, Modal, DatePicker, Select — thay thế trực tiếp Streamlit widgets |
| State & API | **TanStack Query (React Query)** | Auto-cache, refetch, loading states — thay thế `st.session_state` + `st.rerun()` |
| Routing | **React Router v6** | Client-side routing thay cho `active_view` session state |
| Charts | **Ant Design Charts** hoặc **Recharts** | Thay thế Vega-Lite charts |
| HTTP Client | **Axios** | API calls đến Flask backend |
| Auth | **Flask-Login + JWT** | Cookie-based session + JWT cho API |
| Form | **Ant Design Form** | Built-in validation, dynamic fields |
| Table | **Ant Design Table** | Sorting, filtering, pagination, inline editing |
| File Upload | **Ant Design Upload** | Drag & drop, multi-file, progress |
| Toast/Alert | **Ant Design message/notification** | Thay thế `st.toast()`, `st.success()`, `st.error()` |

---

## Phase 0 — Thiết lập Project Structure (2-3 ngày)

### Mục tiêu
Tạo cấu trúc monorepo với Flask API + React SPA, cấu hình dev server, proxy, và verify chạy được.

### Cấu trúc thư mục mới

```
e:\New project\
├── api/                          # Flask API (MỚI)
│   ├── __init__.py               # Flask app factory
│   ├── config.py                 # App configuration
│   ├── extensions.py             # Flask extensions (login, cors)
│   ├── blueprints/
│   │   ├── __init__.py
│   │   ├── auth.py               # POST /api/auth/login, /logout, /me
│   │   ├── dashboard.py          # GET /api/dashboard/stats, /revenue
│   │   ├── cases.py              # CRUD /api/cases
│   │   ├── documents.py          # /api/cases/:id/documents
│   │   ├── entry.py              # POST /api/entry/upload, /extract
│   │   ├── sobo.py               # CRUD /api/sobo
│   │   ├── organizations.py      # CRUD /api/organizations
│   │   ├── delivery.py           # CRUD /api/delivery
│   │   ├── templates_bp.py       # CRUD /api/templates
│   │   └── settings.py           # GET/PUT /api/settings
│   └── middleware/
│       ├── auth.py               # JWT/session middleware
│       └── error_handler.py      # Global error handling
├── web/                          # React SPA (MỚI)
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx
│   │   ├── api/                  # API client layer
│   │   │   ├── client.js         # Axios instance
│   │   │   ├── auth.js
│   │   │   ├── cases.js
│   │   │   ├── dashboard.js
│   │   │   └── ...
│   │   ├── components/           # Shared components
│   │   │   ├── Layout.jsx        # App shell + nav
│   │   │   ├── ProtectedRoute.jsx
│   │   │   └── ...
│   │   ├── pages/                # Page components
│   │   │   ├── Login.jsx
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Cases.jsx
│   │   │   ├── Entry.jsx
│   │   │   ├── Sobo.jsx
│   │   │   ├── Organizations.jsx
│   │   │   ├── Delivery.jsx
│   │   │   ├── Templates.jsx
│   │   │   └── Settings.jsx
│   │   ├── hooks/                # Custom hooks
│   │   ├── store/                # Global state (nếu cần)
│   │   └── styles/
│   │       └── theme.js          # Ant Design theme config
│   └── public/
├── src/                          # Backend modules (GIỮA NGUYÊN)
├── data/                         # Data files (GIỮA NGUYÊN)
├── main.py                       # Sửa lại orchestration
└── requirements.txt              # Thêm flask, flask-cors, flask-login, pyjwt
```

### API endpoints cần tạo (Phase 0)

```
GET  /api/health                  → { "status": "ok" }
```

### Verification
- [ ] Flask API chạy được trên port 5000
- [ ] React dev server chạy được trên port 5173
- [ ] Vite proxy `/api/*` đến Flask 5000
- [ ] Hot reload hoạt động cả 2 phía

---

## Phase 1 — Authentication (2 ngày)

### Mục tiêu
Login/logout, session management, role-based access (admin vs guest).

### API endpoints

```
POST /api/auth/login              → { username, password } → { user, token }
POST /api/auth/logout             → Invalidate session
GET  /api/auth/me                 → Current user info + role
```

### Backend (Flask)
- Tái sử dụng logic từ [auth.py](file:///e:/New%20project/src/auth.py): hàm `authenticate()`, `_create_auth_token()`, `_validate_auth_token()`
- Chuyển sang Flask-Login `UserMixin` + JWT cookie
- 2 roles: `admin` (full access) và `guest` (chỉ xem sobo)

### Frontend (React)
- `Login.jsx` — Form đăng nhập (thay thế `render_login_gate()`)
- `ProtectedRoute.jsx` — Route guard kiểm tra auth
- `useAuth()` hook — Auth state management
- `Layout.jsx` — App shell với header nav (thay thế `render_app_header()`)

### CSS Theme
- Migrate toàn bộ CSS từ [ui_theme.py](file:///e:/New%20project/src/ui_theme.py) sang `theme.js` (Ant Design ConfigProvider)
- Giữ nguyên design tokens: colors, typography, radius, shadows

### Verification
- [ ] Login với admin credentials → redirect dashboard
- [ ] Login với guest credentials → redirect sobo
- [ ] Unauthorized request → 401 → redirect login
- [ ] Logout → clear session → redirect login

---

## Phase 2 — Dashboard (3 ngày)

### Mục tiêu
Dashboard với KPI cards, biểu đồ doanh thu, bảng hồ sơ gần đây.

### API endpoints

```
GET  /api/dashboard/stats?year=2026&branch=...&staff=...
  → { year_projected, year_paid, year_unpaid, month_projected,
      total_cases, status_counts, monthly_revenue[] }

GET  /api/dashboard/recent-cases?limit=20
  → [{ case_id, contract_number, customer_info, status, ... }]

GET  /api/dashboard/filters
  → { years[], branches[], staff_names[], statuses[] }
```

### Backend
- Tái sử dụng: `sqlite_store.get_revenue_summary()`, `sqlite_store.list_cases()`, `sqlite_store.distinct_values()`
- Tái sử dụng: `render_dashboard_kpi_cards()` logic (chuyển sang JSON response)

### Frontend
- `Dashboard.jsx` — Trang chính
- `KpiCards.jsx` — 4 KPI cards (giữ design từ `ui_theme.py`)
- `RevenueChart.jsx` — Biểu đồ doanh thu (Recharts thay Vega-Lite)
- `DonutChart.jsx` — Biểu đồ trạng thái (CSS conic-gradient giữ nguyên)
- `RecentCasesTable.jsx` — Bảng hồ sơ gần đây
- `DashboardFilters.jsx` — Bộ lọc năm/chi nhánh/nhân viên

### Verification
- [ ] KPI cards hiển thị đúng số liệu
- [ ] Biểu đồ render đúng dữ liệu
- [ ] Filters hoạt động, data refresh khi đổi filter
- [ ] Responsive layout (mobile/tablet/desktop)

---

## Phase 3 — Case Management (5-6 ngày) ⭐ Phức tạp nhất

### Mục tiêu
Bảng quản lý hồ sơ: CRUD, filter, sort, pagination, inline edit, export Excel, bulk actions.

### API endpoints

```
# Case CRUD
GET    /api/cases?page=1&size=20&sort=id&order=desc&search=...&status=...&branch=...
  → { items[], total, page, pages }
GET    /api/cases/:id → Full case detail
POST   /api/cases → Create case
PUT    /api/cases/:id → Update case
DELETE /api/cases/:id → Delete case

# Bulk operations
POST   /api/cases/bulk-create → Create multiple cases
POST   /api/cases/import → Import from Excel file
GET    /api/cases/export?format=xlsx&filters=... → Download Excel

# Case status & payment
PATCH  /api/cases/:id/status → { status: "Hoàn thành" }
PATCH  /api/cases/:id/payment → { payment_status: "Đã thanh toán" }

# Case notes & attachments
GET    /api/cases/:id/notes → [{ note, created_at }]
POST   /api/cases/:id/notes → Add note
GET    /api/cases/:id/attachments → [{ filename, size, url }]
POST   /api/cases/:id/attachments → Upload attachment

# Revenue
GET    /api/cases/revenue?year=2026&month=6&branch=...
  → { summary, monthly_data[], cases[] }

# Filters
GET    /api/cases/filters → { statuses[], branches[], staff[], ... }
```

### Backend
- Tái sử dụng: `sqlite_store.list_cases()`, `sqlite_store.upsert_case()`, `sqlite_store.delete_case()`
- Tái sử dụng: `case_filters.py`, `case_exports.py`, `case_excel_export.py`
- Tái sử dụng: `sqlite_store.get_revenue_summary()`

### Frontend
- `Cases.jsx` — Container page
- `CaseTable.jsx` — Ant Design Table (thay `st.data_editor` + custom grid)
  - Column sorting, filtering
  - Pagination server-side
  - Inline status toggle buttons
  - Row selection cho bulk actions
- `CaseFilterBar.jsx` — Search + filter controls
- `CaseEditModal.jsx` — Edit dialog (thay `edit_case_dialog`)
- `CaseDeleteConfirm.jsx` — Delete confirmation
- `CaseImportModal.jsx` — Excel import dialog
- `CaseExportButton.jsx` — Excel export
- `CaseRevenueTab.jsx` — Revenue sub-view với chart + metrics
- `CaseNotes.jsx` — Notes panel
- `CaseAttachments.jsx` — Attachment upload/download

### Verification
- [ ] Table hiển thị đúng data, sorting, pagination
- [ ] Search tìm kiếm real-time
- [ ] Filter by status, branch, staff, date range
- [ ] CRUD operations (tạo/sửa/xóa hồ sơ)
- [ ] Inline status toggle
- [ ] Excel import/export
- [ ] Notes & attachments

---

## Phase 4 — Case Documents (4 ngày)

### Mục tiêu
Tạo văn bản, preview, gửi email, download ZIP.

### API endpoints

```
# Document generation
POST   /api/cases/:id/documents/generate
  → { documents: [{ name, type, url }] }

GET    /api/cases/:id/documents
  → [{ name, type, size, url, preview_url }]

# Preview
GET    /api/cases/:id/documents/:doc_name/preview
  → HTML rendered preview

# Download
GET    /api/cases/:id/documents/:doc_name/download
  → File download
GET    /api/cases/:id/documents/download-all
  → ZIP download

# Email
POST   /api/cases/:id/documents/send-email
  → { recipients, subject, body, attachments[] }

# Delivery info
GET    /api/delivery/contacts → [{ short_name, full_details }]
POST   /api/cases/:id/documents/delivery
  → { delivery_contact, tracking_number }

# Phat hanh (certificate issuance)
POST   /api/cases/:id/phathanh/reply-email
  → Send certificate reply email
```

### Backend
- Tái sử dụng: `document_exporter.render_docx_template()`, `render_docx_preview_html()`
- Tái sử dụng: `case_exports.generate_case_documents()`
- Tái sử dụng: `mail_service.py`, `email_reply_service.py`
- Tái sử dụng: `case_packager.py`

### Frontend
- `CaseDocuments.jsx` — Document panel trong case detail
- `DocumentPreview.jsx` — HTML preview trong modal/drawer
- `SendEmailModal.jsx` — Email compose dialog
- `DeliveryInfoModal.jsx` — Chọn thông tin chuyển phát
- `DocumentDownload.jsx` — Download individual/ZIP

### Verification
- [ ] Generate documents cho case
- [ ] Preview hiển thị đúng nội dung
- [ ] Download file/ZIP hoạt động
- [ ] Gửi email với attachments
- [ ] Delivery info dialog

---

## Phase 5 — Entry Form + OCR (4-5 ngày)

### Mục tiêu
Upload file → AI OCR extract → Review & edit → Save to database.

### API endpoints

```
# File upload
POST   /api/entry/upload → Upload PDF/images
  → { upload_id, files: [{ name, pages, thumbnails[] }] }

# OCR extraction
POST   /api/entry/extract
  → { extraction: { customer_info, address, so_thua, ... } }
  (Long-running → SSE or polling)

# Entry form
GET    /api/entry/form-options → Dropdown options from Excel template
POST   /api/entry/save → Save extraction to case
GET    /api/entry/excel-template → Download filled Excel

# Page preview
GET    /api/entry/upload/:upload_id/page/:page_num?rotation=0
  → Page image

# Form defaults
GET    /api/entry/defaults → Default form values
```

### Backend
- Tái sử dụng: `gemini_extractor.extract_fields()`, `ocr_accumulator.py`
- Tái sử dụng: `extractor.py`, `preview.py`, `image_annotator.py`
- Tái sử dụng: `excel_writer.load_dropdown_options()`, `excel_writer.fill_template()`
- Tái sử dụng: `sqlite_store.upsert_case()`

### Frontend
- `Entry.jsx` — Container page (2 panels: viewer + form)
- `FileUploader.jsx` — Drag & drop multi-file upload
- `PageViewer.jsx` — PDF page preview với rotation controls
- `OcrProgress.jsx` — OCR extraction progress
- `EntryForm.jsx` — Complex form (20+ fields, tabs, dropdowns)
  - Tab "Thông tin khách hàng" 
  - Tab "Thông tin tài sản"
  - Dynamic fields based on case type (cá nhân/tổ chức)
- `ExtractionReview.jsx` — Review AI results before applying

### Verification
- [ ] Upload multiple PDF/images
- [ ] Page viewer với zoom/rotation
- [ ] AI extraction hoạt động
- [ ] Form điền đúng data từ extraction
- [ ] Save tạo case mới trong DB
- [ ] Download filled Excel template

---

## Phase 6 — Sobo View (3 ngày)

### Mục tiêu
Quản lý yêu cầu thẩm định sơ bộ: danh sách, tìm kiếm, xem chi tiết, download GCN.

### API endpoints

```
# Sobo CRUD
GET    /api/sobo?search=...&status=...&page=1&size=20
  → { items[], total }
GET    /api/sobo/:id → Full sobo detail
PUT    /api/sobo/:id → Update sobo record
DELETE /api/sobo/:id → Delete sobo record

# Sobo files
GET    /api/sobo/:id/files → [{ filename, url }]
GET    /api/sobo/:id/files/download → Single file or ZIP

# Sobo from case
POST   /api/sobo/from-case/:case_id → Create sobo from existing case
```

### Backend
- Tái sử dụng: `database_manager.list_sobo_records()`, `upsert_sobo_record()`, `delete_sobo_record()`
- Tái sử dụng: `sobo_handler.py` business logic (region mapping, email sending)

### Frontend
- `Sobo.jsx` — Container page
- `SoboTable.jsx` — Sobo list table
- `SoboDetailDrawer.jsx` — Xem chi tiết (Ant Design Drawer)
- `SoboEditModal.jsx` — Sửa sobo record
- `SoboFromCaseModal.jsx` — Tạo sobo từ case

### Verification
- [ ] Danh sách sobo với search/filter
- [ ] Xem chi tiết sobo
- [ ] Sửa/xóa sobo record
- [ ] Download GCN files
- [ ] Guest user chỉ thấy view này

---

## Phase 7 — Organizations + Delivery (3 ngày)

### Mục tiêu
Quản lý tổ chức + liên hệ chuyển phát.

### API endpoints

```
# Organizations
GET    /api/organizations?search=...
  → [{ id, tax_code, name, abbreviation, representative }]
POST   /api/organizations → Create
PUT    /api/organizations/:id → Update
DELETE /api/organizations/:id → Delete
POST   /api/organizations/merge → Merge two orgs
POST   /api/organizations/ai-extract → AI extract from uploaded docs

# Delivery contacts
GET    /api/delivery?search=...
  → [{ id, short_name, full_details, case_count }]
POST   /api/delivery → Create contact
PUT    /api/delivery/:id → Update contact
DELETE /api/delivery/:id → Delete contact
```

### Backend
- Tái sử dụng: `sqlite_store.list_organizations()`, `upsert_organization()`, `delete_organization()`, `merge_organizations()`
- Tái sử dụng: `database_manager.list_delivery_contacts()`, `upsert_delivery_contact()`
- Tái sử dụng: `gemini_extractor.extract_fields()` cho AI org extraction

### Frontend
- `Organizations.jsx` — Org management page
- `OrgEditModal.jsx` — Create/edit org
- `OrgMergeModal.jsx` — Merge organizations
- `OrgAiExtract.jsx` — Upload docs → AI extract org info
- `Delivery.jsx` — Delivery contacts page
- `DeliveryEditModal.jsx` — Create/edit delivery contact

### Verification
- [ ] CRUD tổ chức
- [ ] Merge tổ chức
- [ ] AI extract organization info
- [ ] CRUD delivery contacts

---

## Phase 8 — Templates + Settings (3 ngày)

### Mục tiêu
Quản lý Word templates + Cấu hình hệ thống (OAuth2, paths, etc).

### API endpoints

```
# Templates
GET    /api/templates → [{ name, path, last_modified }]
GET    /api/templates/:name → Template detail + placeholders
PUT    /api/templates/:name → Upload/update template
GET    /api/templates/:name/history → Version history
GET    /api/templates/:name/preview → Preview with sample data

# Settings
GET    /api/settings → All settings (paths, OAuth status, etc.)
PUT    /api/settings → Update settings

# OAuth2
GET    /api/settings/oauth/:provider/auth-url → Get OAuth2 authorization URL
POST   /api/settings/oauth/:provider/callback → Exchange code for tokens
DELETE /api/settings/oauth/:provider → Disconnect OAuth

# Backup
POST   /api/settings/backup → Create backup
GET    /api/settings/backup/download → Download backup ZIP
POST   /api/settings/backup/restore → Upload & restore backup
```

### Backend
- Tái sử dụng: `template_manager.py` 
- Tái sử dụng: `oauth2_service.py`
- Tái sử dụng: `backup_service.py`

### Frontend
- `Templates.jsx` — Template list page
- `TemplateEditor.jsx` — Edit template + placeholder list
- `TemplateHistory.jsx` — Version history viewer
- `Settings.jsx` — Settings page với tabs
  - Tab "Đường dẫn" — Path configuration
  - Tab "OAuth2" — Google/Outlook connection
  - Tab "Backup" — Backup/restore
  - Tab "Hệ thống" — System info

### Verification
- [ ] List/edit templates
- [ ] OAuth2 connect/disconnect Google & Outlook
- [ ] Backup & restore database

---

## Phase 9 — Integration & Polish (4-5 ngày)

### Mục tiêu
Tích hợp background services, deployment setup, testing, polish UI.

### Tasks
1. **Main orchestrator**: Sửa `main.py` để chạy Flask thay Streamlit
2. **Background services**: Cập nhật `background_services.py` (thay `start_streamlit` → `start_flask`)
3. **Deployment**:
   - Docker Compose: Flask + React + Nginx
   - Nginx config: serve React static + proxy `/api` → Flask
   - Production build: `vite build` → static files
4. **Testing**: Integration tests cho tất cả API endpoints
5. **UI Polish**:
   - Responsive design
   - Loading states, error boundaries
   - Keyboard shortcuts
   - Dark mode (optional)
6. **Data migration**: Verify existing data works with new system

### Verification
- [ ] All 3 processes start correctly (Flask + Telegram + Mail Listener)
- [ ] Production build works
- [ ] Nginx serves React + proxies API
- [ ] All features from Streamlit version work in new version
- [ ] Mobile responsive

---

## Bảng tổng hợp tiến độ

| Phase | Mô tả | Ngày | Phụ thuộc | Trạng thái |
|-------|--------|------|-----------|-----------|
| 0 | Project Structure | 2-3 | — | ⬜ |
| 1 | Authentication | 2 | Phase 0 | ⬜ |
| 2 | Dashboard | 3 | Phase 1 | ⬜ |
| 3 | Case Management | 5-6 | Phase 1 | ⬜ |
| 4 | Case Documents | 4 | Phase 3 | ⬜ |
| 5 | Entry Form + OCR | 4-5 | Phase 1 | ⬜ |
| 6 | Sobo View | 3 | Phase 1 | ⬜ |
| 7 | Orgs + Delivery | 3 | Phase 1 | ⬜ |
| 8 | Templates + Settings | 3 | Phase 1 | ⬜ |
| 9 | Integration + Polish | 4-5 | All | ⬜ |
| | **TỔNG** | **35-45** | | |

> [!NOTE]
> Phase 2, 3, 5, 6, 7, 8 có thể chạy **song song** sau khi Phase 1 hoàn thành (chúng chỉ phụ thuộc vào auth layer).

---

## Lưu ý quan trọng

> [!WARNING]
> **Không xóa code Streamlit cũ** cho đến khi Flask version hoạt động 100%. Giữ song song 2 version trong cùng repo, chỉ khác entry point (`app.py` cho Streamlit, `api/__init__.py` cho Flask).

> [!CAUTION]
> Phase 3 (Case Management) là **phức tạp nhất** — nên làm trước và dành nhiều thời gian test. Đây là core feature của hệ thống.
