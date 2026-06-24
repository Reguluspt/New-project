# Prompts thực thi: Chuyển đổi Streamlit → Flask + React (Vite) SPA

> Mỗi prompt dưới đây là **self-contained** — có thể copy riêng từng cái để feed vào AI assistant thực thi từng phase.
> Thứ tự thực hiện: Phase 0 → 1 → (2,3,5,6,7,8 song song) → 4 (sau 3) → 9 (cuối cùng).

---

## PROMPT — PHASE 0: Thiết lập Project Structure

```
Tôi đang chuyển đổi một ứng dụng Streamlit Python sang kiến trúc Flask REST API + React SPA (Vite).

## Codebase hiện tại (KHÔNG SỬA, CHỈ THÊM MỚI)
- Thư mục gốc: e:\New project
- Backend modules: src/ (30+ file Python — giữ nguyên 100%)
- Views Streamlit: views/ (20 file — sẽ thay thế dần bằng React)
- Database: SQLite (data/cases.db + data/telegram_records.db)
- Entry point hiện tại: app.py (Streamlit), main.py (orchestrator)
- Dependencies hiện tại: xem requirements.txt

## Nhiệm vụ Phase 0
Tạo cấu trúc monorepo với Flask API backend + React SPA frontend, chạy song song với code Streamlit hiện tại (không xóa gì cả).

### 1. Tạo Flask API backend (thư mục api/)

Tạo cấu trúc:
```
api/
├── __init__.py          # Flask app factory: create_app()
├── config.py            # Config class (SECRET_KEY, DB paths, CORS origins)
├── extensions.py        # Init Flask extensions (CORS, Login manager)
├── blueprints/
│   ├── __init__.py      # Register all blueprints
│   └── health.py        # GET /api/health → {"status": "ok", "version": "2.0"}
├── middleware/
│   ├── __init__.py
│   ├── auth.py          # @login_required decorator cho API
│   └── error_handler.py # Global JSON error handler (400, 401, 404, 500)
└── run.py               # Entry point: python -m api.run (port 5000)
```

Yêu cầu cho api/__init__.py:
- Flask app factory pattern: create_app(config_name="default")
- Load .env từ API.env (dùng python-dotenv)
- CORS cho localhost:5173 (React dev server)
- JSON error handlers cho 400, 401, 403, 404, 500
- Register blueprints với prefix /api

Yêu cầu cho api/config.py:
- Đọc SECRET_KEY từ env hoặc generate random
- SQLITE_DATABASE = Path("data/cases.db")
- RECORDS_DB = Path("data/telegram_records.db")  
- CORS_ORIGINS = ["http://localhost:5173"]
- Tái sử dụng paths từ src/app_config.py (import DATA_DIR, OUTPUT_DIR, etc.)

### 2. Tạo React SPA frontend (thư mục web/)

Dùng Vite + React:
```bash
cd "e:\New project"
npx -y create-vite@latest web -- --template react
cd web
npm install antd @ant-design/icons axios react-router-dom @tanstack/react-query
```

Cấu trúc src/:
```
web/src/
├── main.jsx             # ReactDOM.createRoot + providers
├── App.jsx              # React Router routes
├── api/
│   └── client.js        # Axios instance (baseURL: /api, withCredentials: true)
├── components/
│   └── Layout.jsx       # Placeholder app shell
├── pages/
│   └── HealthCheck.jsx  # Gọi GET /api/health, hiển thị kết quả
└── styles/
    └── theme.js         # Ant Design ConfigProvider theme tokens
```

Yêu cầu cho vite.config.js:
- Proxy /api → http://localhost:5000 (Flask dev server)
- Đảm bảo HMR hoạt động

Yêu cầu cho theme.js (migrate từ src/ui_theme.py):
```js
export const theme = {
  token: {
    colorPrimary: '#0f6cbd',
    colorPrimaryHover: '#0057d8',
    colorBgContainer: '#ffffff',
    colorBgLayout: '#f5f7fb',
    colorText: '#0f172a',
    colorTextSecondary: '#64748b',
    borderRadius: 12,
    fontFamily: '"Segoe UI", system-ui, -apple-system, sans-serif',
    colorError: '#be123c',
    colorSuccess: '#047857',
    colorWarning: '#c2410c',
  },
};
```

### 3. Cập nhật requirements.txt
Thêm vào requirements.txt (không xóa dòng cũ):
```
flask==3.1.1
flask-cors==5.0.1
flask-login==0.6.3
pyjwt==2.10.1
```

### 4. Tạo script khởi động
Tạo file run_dev.bat:
```bat
@echo off
echo Starting Flask API on port 5000...
start "Flask API" cmd /k "cd /d e:\New project && .venv\Scripts\python -m api.run"
echo Starting React dev server on port 5173...
start "React Dev" cmd /k "cd /d e:\New project\web && npm run dev"
echo Both servers starting. API: http://localhost:5000, Web: http://localhost:5173
```

### Verification
Sau khi hoàn thành, verify:
1. Chạy `python -m api.run` → Flask chạy port 5000
2. GET http://localhost:5000/api/health → {"status": "ok"}
3. Chạy `cd web && npm run dev` → React chạy port 5173
4. Truy cập http://localhost:5173 → React app hiện
5. React gọi /api/health qua proxy → hiển thị response
6. Code Streamlit cũ vẫn chạy được bình thường (app.py không bị sửa)
```

---

## PROMPT — PHASE 1: Authentication

```
Tiếp tục dự án chuyển đổi Streamlit → Flask + React SPA.

## Context
- Flask API đã chạy tại api/ (Phase 0 hoàn thành)
- React SPA đã chạy tại web/ với Ant Design
- Hệ thống auth hiện tại nằm trong src/auth.py, sử dụng:
  - 2 loại user: admin (từ env APP_LOGIN_USERNAME/APP_LOGIN_PASSWORD) và guest (APP_GUEST_USERNAME/APP_GUEST_PASSWORD, mặc định "khach"/"Cen2026")
  - HMAC-SHA256 signed token với 30-day expiry
  - Cookie-based auth (cookie name: "thamdinh_auth")
  - Guest user chỉ được xem view "sobo"

## Nhiệm vụ Phase 1

### 1. Flask Auth Blueprint (api/blueprints/auth.py)

Tạo 3 endpoints:

**POST /api/auth/login**
- Body: { "username": "...", "password": "..." }
- Tái sử dụng hàm authenticate() từ src/auth.py
- Nếu thành công: set HTTP-only cookie với JWT token, return { "user": { "username": "...", "role": "admin"|"guest" } }
- Nếu thất bại: return 401 { "error": "Tên tài khoản hoặc mật khẩu không đúng" }
- JWT payload: { "sub": username, "role": "admin"|"guest", "exp": now + 30 days }
- Dùng SECRET_KEY từ app config

**POST /api/auth/logout**
- Clear auth cookie
- Return { "message": "Đã đăng xuất" }

**GET /api/auth/me**
- Đọc JWT từ cookie, validate
- Return { "user": { "username": "...", "role": "admin"|"guest" } }
- Nếu cookie invalid/expired: return 401

### 2. Auth Middleware (api/middleware/auth.py)

Tạo decorator `@login_required`:
- Đọc JWT token từ cookie "thamdinh_auth"
- Validate signature + expiry
- Set g.current_user = { "username": ..., "role": ... }
- Nếu invalid: return 401 JSON

Tạo decorator `@admin_required`:
- Extends @login_required
- Kiểm tra role == "admin", nếu không return 403

### 3. React Auth (web/src/)

**web/src/api/auth.js**
```js
import client from './client';
export const login = (username, password) => client.post('/auth/login', { username, password });
export const logout = () => client.post('/auth/logout');
export const getMe = () => client.get('/auth/me');
```

**web/src/hooks/useAuth.js**
- Custom hook quản lý auth state
- Khi app mount: gọi getMe() để check session
- Expose: { user, isLoading, isAuthenticated, isGuest, login, logout }
- Lưu user state trong React Context

**web/src/components/ProtectedRoute.jsx**
- Wrap routes cần auth
- Nếu chưa login → redirect /login
- Nếu là guest → chỉ cho phép route /sobo

**web/src/pages/Login.jsx**
- UI giống login hiện tại (xem CSS class .login-brand, .login-title, .login-subtitle, .st-key-login_panel trong src/ui_theme.py)
- Ant Design Form với username + password fields
- Submit → gọi login API → redirect dashboard (admin) hoặc /sobo (guest)
- Hiển thị error message khi sai credentials
- Design:
  - Centered card (max-width 420px)
  - Title: "Hệ Thống Thẩm Định" (color: #0f6cbd, font-size: 28px, font-weight: 750)
  - Subtitle: "Đăng nhập để tiếp tục quản lý hồ sơ" (color: #64748b)
  - Background: #f5f7fb
  - Card: white, border-radius: 8px, box-shadow: 0 18px 50px rgba(22,39,70,0.10)

**web/src/components/Layout.jsx**
- App shell với fixed top header (height: 64px)
- Logo/brand: "Hệ Thống Thẩm Định" + "Phòng Kinh Doanh"
- Navigation items (dùng react-router NavLink):
  - Admin: Dashboard, Nhập hồ sơ, Quản lý hồ sơ, Sơ bộ, Tổ chức, Chuyển phát, Templates, Cấu hình
  - Guest: chỉ Sơ bộ
- User avatar (chữ cái đầu tên) + nút Đăng xuất
- Active nav item: color #0057d8, bottom border 3px solid
- Icons: dùng Ant Design Icons (DashboardOutlined, FileSearchOutlined, FolderOutlined, etc.)
- Responsive: ẩn text label trên mobile, chỉ hiện icon

**web/src/App.jsx**
- React Router v6 routes:
  - /login → Login (public)
  - / → redirect /dashboard
  - /dashboard → Dashboard (admin only)
  - /entry → Entry (admin only)
  - /cases → Cases (admin only)
  - /sobo → Sobo (admin + guest)
  - /organizations → Organizations (admin only)
  - /delivery → Delivery (admin only)
  - /templates → Templates (admin only)
  - /settings → Settings (admin only)
- Tất cả routes trừ /login wrap trong ProtectedRoute + Layout

### Verification
1. POST /api/auth/login với đúng credentials → 200 + cookie set
2. POST /api/auth/login sai → 401
3. GET /api/auth/me với valid cookie → user info
4. GET /api/auth/me không có cookie → 401
5. React login page hiển thị đúng UI
6. Login → redirect đúng page theo role
7. Truy cập protected route khi chưa login → redirect /login
8. Guest truy cập /dashboard → redirect /sobo
9. Logout → clear cookie → redirect /login
10. Refresh page → vẫn giữ session (cookie persistent)
```

---

## PROMPT — PHASE 2: Dashboard

```
Tiếp tục dự án chuyển đổi Streamlit → Flask + React SPA.

## Context
- Auth đã hoạt động (Phase 1). User đã login được, Layout có header nav.
- Database: data/cases.db (SQLite), managed bởi src/sqlite_store.py
- Dashboard hiện tại (views/dashboard.py) hiển thị:
  - 4 KPI cards: Doanh thu dự kiến cả năm, Đã thanh toán, Công nợ tồn, Doanh thu tháng
  - Biểu đồ grouped bar chart (doanh thu vs công nợ theo tháng) — dùng st.vega_lite_chart
  - Biểu đồ donut chart trạng thái hồ sơ — dùng CSS conic-gradient
  - Bảng hồ sơ gần đây
  - Filters: năm, chi nhánh, nhân viên thẩm định, trạng thái

## Nhiệm vụ Phase 2

### 1. Flask Blueprint (api/blueprints/dashboard.py)

**GET /api/dashboard/stats**
Query params: year, branch, staff_name, status (tất cả optional)
Response:
```json
{
  "year_projected": 1500000000,
  "year_paid": 800000000,
  "year_unpaid": 700000000,
  "month_projected": 120000000,
  "selected_month": "06",
  "total_cases": 245,
  "status_counts": {
    "Đang thực hiện": 45,
    "Hoàn thành": 150,
    "Đã phát hành": 30,
    "Hủy": 20
  },
  "monthly_revenue": [
    { "month": "01", "projected": 100000000, "paid": 80000000, "unpaid": 20000000 }
  ]
}
```
Logic: 
- Import từ src/sqlite_store: init_db, list_cases, get_revenue_summary
- sqlite_db_path = current_app.config["SQLITE_DATABASE"]
- Gọi get_revenue_summary(db, year=year, filters...)
- Gọi list_cases(db) với filters để đếm status

**GET /api/dashboard/recent-cases**
Query params: limit (default 20), year, branch, staff_name
Response: [{ case_id, contract_number, customer_info, status, execution_month, valuation_fee, payment_status }]
Logic: Gọi list_cases(db, ...) với sort by id desc, limit

**GET /api/dashboard/filters**
Response:
```json
{
  "years": ["2024", "2025", "2026"],
  "branches": ["Chi nhánh A", "Chi nhánh B"],
  "staff_names": ["Nguyễn Văn A", "Trần Thị B"],
  "statuses": ["Đang thực hiện", "Hoàn thành", "Đã phát hành", "Hủy"]
}
```
Logic: Gọi sqlite_store.distinct_values(db, column) cho mỗi field

### 2. React Dashboard (web/src/pages/Dashboard.jsx)

**Layout:**
- Top: Filter bar (4 Select dropdowns: Năm, Chi nhánh, Nhân viên, Trạng thái)
- Row 1: 4 KPI cards (grid 4 columns, responsive 2→1 trên mobile)
- Row 2: 2 columns — Bar chart (8 cols) + Donut chart (4 cols)
- Row 3: Bảng hồ sơ gần đây

**KPI Cards (web/src/components/dashboard/KpiCards.jsx):**
Giữ nguyên design từ ui_theme.py (.dashboard-kpi-card CSS):
- Card 1: "Doanh thu dự kiến cả năm" — format triệu VND
- Card 2: "Đã thanh toán cả năm" — có progress bar (tỷ lệ thu)
- Card 3: "Công nợ tồn cả năm" — có warning icon
- Card 4 (primary/blue): "Doanh thu dự kiến trong tháng" — có badge "Đạt X% Target"
- Style: border-radius 12px, border 1px solid #dbe3f3, padding 16px 18px
- Card 4: background #0f6cbd, text white

**Revenue Chart (web/src/components/dashboard/RevenueChart.jsx):**
- Dùng Recharts BarChart (grouped bars)
- X axis: tháng (01-12)
- 2 bars: Doanh thu dự kiến (blue) vs Công nợ (red/orange)
- Tooltip hiển thị số tiền format VND

**Status Donut (web/src/components/dashboard/StatusDonut.jsx):**
- CSS conic-gradient donut chart (giữ nguyên approach từ dashboard.py hiện tại)
- Legend bên dưới với màu + label + count
- Colors: Đang thực hiện=#f59e0b, Hoàn thành=#10b981, Đã phát hành=#3b82f6, Hủy=#ef4444

**Recent Cases Table (web/src/components/dashboard/RecentCases.jsx):**
- Ant Design Table, compact mode
- Columns: STT, Số HĐ, Khách hàng, Tháng TH, Phí thẩm định, Trạng thái, Thanh toán
- Status column: colored badges
- Click row → navigate to /cases?id=xxx

**Filters (web/src/components/dashboard/DashboardFilters.jsx):**
- 4 Ant Design Select (allowClear, placeholder)
- Khi thay đổi filter → refetch data (dùng TanStack Query với filter params)

### 3. API Client (web/src/api/dashboard.js)
```js
import client from './client';
export const getStats = (params) => client.get('/dashboard/stats', { params });
export const getRecentCases = (params) => client.get('/dashboard/recent-cases', { params });
export const getFilters = () => client.get('/dashboard/filters');
```

### 4. Custom Hook (web/src/hooks/useDashboard.js)
- Dùng useQuery từ TanStack Query
- Auto refetch khi filter params thay đổi
- Loading + error states

### Verification
1. GET /api/dashboard/stats → trả đúng số liệu
2. GET /api/dashboard/filters → trả danh sách filter options
3. 4 KPI cards hiển thị đúng số, format triệu VND
4. Bar chart render đúng data theo tháng
5. Donut chart hiển thị đúng tỷ lệ trạng thái
6. Thay đổi filter → data refresh
7. Recent cases table hiển thị đúng
8. Responsive: 4 cards → 2 → 1 trên mobile
```

---

## PROMPT — PHASE 3: Case Management (Quản lý hồ sơ)

```
Tiếp tục dự án chuyển đổi Streamlit → Flask + React SPA.

## Context
- Auth + Dashboard đã hoạt động.
- Đây là PHASE PHỨC TẠP NHẤT — core feature của hệ thống.
- Case data model (src/sqlite_store.py) có ~35 fields:
  contract_number, customer_info, customer_info_2, phone, id_number,
  address, asset_description, asset_address, so_thua, so_to, dien_tich,
  purpose, province, district, ward, branch, execution_month,
  valuation_fee, collection_fee, total_fee, payment_status,
  appraiser_name, appraiser_2, status, certificate_number,
  bank_name, credit_type, notes, delivery_method, web_case_id,
  source, received_date, completed_date, issued_date, ...
- Views hiện tại: views/case_table.py (917 dòng), views/case_dialogs.py (367 dòng), views/cases.py (187 dòng)

## Nhiệm vụ Phase 3

### 1. Flask Blueprint (api/blueprints/cases.py)

**GET /api/cases** — Danh sách hồ sơ (paginated, filtered, sorted)
Query params:
- page (default 1), size (default 20)
- sort (default "id"), order (default "desc")
- search (tìm kiếm toàn bộ fields)
- status, branch, appraiser_name, execution_month, payment_status (filter)
- year (filter by execution_month year)
Response:
```json
{
  "items": [{ "id": 1, "contract_number": "01/2026/HDTD", "..." : "..." }],
  "total": 245,
  "page": 1,
  "pages": 13,
  "size": 20
}
```
Logic: Dùng sqlite_store.list_cases(db, filters, sort, page, size)

**GET /api/cases/:id** — Chi tiết 1 hồ sơ
Response: { "id": 1, "contract_number": "...", ... (tất cả fields) }

**POST /api/cases** — Tạo hồ sơ mới
Body: { contract_number, customer_info, address, ... }
Logic: sqlite_store.upsert_case(db, case_data)

**PUT /api/cases/:id** — Cập nhật hồ sơ
Body: { fields to update }
Logic: sqlite_store.upsert_case(db, {id: id, ...updated_fields})

**DELETE /api/cases/:id** — Xóa hồ sơ
Logic: sqlite_store.delete_case(db, id)

**PATCH /api/cases/:id/status** — Cập nhật trạng thái
Body: { "status": "Hoàn thành" }

**PATCH /api/cases/:id/payment** — Cập nhật thanh toán
Body: { "payment_status": "Đã thanh toán" }

**POST /api/cases/import** — Import từ Excel
Body: multipart/form-data với file Excel
Logic: sqlite_store.import_from_excel(db, file_path)

**GET /api/cases/export** — Export Excel
Query params: filters (same as GET /api/cases)
Response: Excel file download
Logic: Dùng case_excel_export.py hoặc excel_writer.py

**GET /api/cases/filters** — Danh sách filter options
Response: { statuses[], branches[], appraisers[], execution_months[], payment_statuses[] }

**GET /api/cases/:id/notes** — Danh sách ghi chú
**POST /api/cases/:id/notes** — Thêm ghi chú
Body: { "note": "Nội dung ghi chú" }

### 2. React Pages & Components

**web/src/pages/Cases.jsx** — Container page
- 2 tabs: "Quản lý hồ sơ" + "Doanh thu"
- Tab 1 → CaseTable
- Tab 2 → CaseRevenue

**web/src/components/cases/CaseTable.jsx** — Bảng chính
- Ant Design Table với:
  - Server-side pagination (gọi API với page, size)
  - Server-side sorting (gọi API với sort, order)
  - Column filters inline
  - Row selection (checkbox) cho bulk actions
- Columns hiển thị:
  STT, Số HĐ, Khách hàng, Địa chỉ TS, Tháng TH, Phí TD, Thanh toán, Trạng thái, Thao tác
- Payment status: Click để toggle (PATCH /api/cases/:id/payment)
- Status: Colored Tag (Ant Design Tag)
  - "Đang thực hiện" → gold
  - "Hoàn thành" → green
  - "Đã phát hành" → blue
  - "Hủy" → red
- Action column: buttons Sửa, Xóa, Xem tài liệu (link to case documents)
- Top toolbar: Search input + Filter button + Export button + Import button + Add button

**web/src/components/cases/CaseFilterBar.jsx** — Filter bar
- Search input (debounced, 300ms)
- Filter popover/drawer với:
  - Trạng thái (multi-select)
  - Chi nhánh (select)
  - Nhân viên TD (select)
  - Tháng thực hiện (date range)
  - Trạng thái thanh toán (select)
- "Xóa bộ lọc" button

**web/src/components/cases/CaseEditModal.jsx** — Modal sửa hồ sơ
- Ant Design Modal (width: 900px)
- Ant Design Form với tất cả fields, chia thành sections:
  - Thông tin hợp đồng: Số HĐ, Ngày nhận, Nguồn, Chi nhánh
  - Thông tin khách hàng: Tên KH, SĐT, CCCD, Địa chỉ
  - Thông tin tài sản: Mô tả TS, Địa chỉ TS, Số thửa, Số tờ, Diện tích, Tỉnh/Huyện/Xã
  - Phí & Thanh toán: Phí TD, Phí thu, Tổng phí, Trạng thái TT
  - Thực hiện: Tháng TH, NV thẩm định, NV thẩm định 2, Trạng thái
  - Phát hành: Số chứng thư, Ngày hoàn thành, Ngày phát hành
  - Ghi chú
- Submit → POST (create) hoặc PUT (update)

**web/src/components/cases/CaseDeleteConfirm.jsx**
- Ant Design Modal.confirm
- "Bạn có chắc muốn xóa hồ sơ [contract_number]?"

**web/src/components/cases/CaseImportModal.jsx**
- Ant Design Upload (dragger) cho file Excel
- Preview imported data trước khi confirm
- Progress bar khi importing

**web/src/components/cases/CaseExportButton.jsx**
- Button download Excel
- Kèm filter hiện tại

**web/src/components/cases/CaseRevenue.jsx** — Tab doanh thu
- Filter bar: năm, tháng, chi nhánh
- 4 Ant Design Statistic cards (tổng DT, đã thu, công nợ, số hồ sơ)
- Recharts LineChart (doanh thu theo tháng)
- Ant Design Table (chi tiết doanh thu từng hồ sơ)

### 3. API Client (web/src/api/cases.js)
```js
import client from './client';
export const listCases = (params) => client.get('/cases', { params });
export const getCase = (id) => client.get(`/cases/${id}`);
export const createCase = (data) => client.post('/cases', data);
export const updateCase = (id, data) => client.put(`/cases/${id}`, data);
export const deleteCase = (id) => client.delete(`/cases/${id}`);
export const updateStatus = (id, status) => client.patch(`/cases/${id}/status`, { status });
export const updatePayment = (id, status) => client.patch(`/cases/${id}/payment`, { payment_status: status });
export const importCases = (file) => { const fd = new FormData(); fd.append('file', file); return client.post('/cases/import', fd); };
export const exportCases = (params) => client.get('/cases/export', { params, responseType: 'blob' });
export const getFilters = () => client.get('/cases/filters');
export const getNotes = (id) => client.get(`/cases/${id}/notes`);
export const addNote = (id, note) => client.post(`/cases/${id}/notes`, { note });
```

### Verification
1. GET /api/cases → paginated list
2. GET /api/cases?search=keyword → filtered results
3. POST /api/cases → create case → verify in DB
4. PUT /api/cases/1 → update case → verify changes
5. DELETE /api/cases/1 → delete case
6. Table hiển thị đúng data, pagination hoạt động
7. Sort by column header click
8. Filter drawer hoạt động
9. Edit modal: load data → edit → save → table refresh
10. Delete confirm → delete → table refresh
11. Import Excel → cases created
12. Export Excel → file download
13. Inline payment status toggle
14. Notes: xem + thêm ghi chú
```

---

## PROMPT — PHASE 4: Case Documents

```
Tiếp tục dự án chuyển đổi Streamlit → Flask + React SPA.

## Context
- Case management đã hoạt động (Phase 3).
- Document generation hiện tại (views/case_documents.py — 1108 dòng):
  - Tạo văn bản Word từ templates (hợp đồng, phiếu yêu cầu, biên bản nghiệm thu, etc.)
  - Preview văn bản dưới dạng HTML
  - Gửi email kèm attachments
  - Download file đơn lẻ hoặc ZIP
  - Chọn thông tin chuyển phát
  - Phát hành chứng thư (reply email)
- Backend modules (giữ nguyên):
  - src/document_exporter.py: render_docx_template(), render_docx_preview_html(), build_placeholder_context()
  - src/case_exports.py: generate_case_documents()
  - src/case_packager.py: package_case_files()
  - src/mail_service.py: send_case_email()
  - src/email_reply_service.py: send_phathanh_reply()
  - src/professional_forwarding.py

## Nhiệm vụ Phase 4

### 1. Flask Blueprint (api/blueprints/documents.py)

**POST /api/cases/:id/documents/generate**
- Tạo tất cả văn bản cho case (dùng case_exports.generate_case_documents)
- Response: { "documents": [{ "name": "Hop_dong_01_2026.docx", "type": "docx", "size": 45000 }] }

**GET /api/cases/:id/documents**
- Liệt kê văn bản đã tạo cho case
- Response: [{ name, type, size, created_at }]

**GET /api/cases/:id/documents/:filename/preview**
- Response: HTML string (dùng render_docx_preview_html)
- Content-Type: text/html

**GET /api/cases/:id/documents/:filename/download**
- Response: file download (Content-Disposition: attachment)

**GET /api/cases/:id/documents/download-all**
- Response: ZIP file download

**POST /api/cases/:id/documents/send-email**
Body:
```json
{
  "recipients": ["email@example.com"],
  "cc": ["cc@example.com"],
  "subject": "Kết quả thẩm định - HĐ 01/2026",
  "body": "Kính gửi...",
  "attachments": ["Hop_dong.docx", "Phieu_yeu_cau.docx"],
  "send_method": "oauth2"
}
```
Logic: Dùng mail_service.send_case_email()

**POST /api/cases/:id/phathanh/reply**
Body: { "certificate_number": "CT-001/2026", "attachments": ["..."] }
Logic: Dùng email_reply_service.send_phathanh_reply()

**GET /api/delivery/contacts**
Response: [{ id, short_name, full_details }]

**POST /api/cases/:id/delivery**
Body: { "delivery_contact_id": 1, "tracking_number": "..." }

### 2. React Components

**web/src/pages/CaseDetail.jsx** — Trang chi tiết hồ sơ
- Route: /cases/:id
- Tabs: Thông tin, Tài liệu, Ghi chú
- Tab "Tài liệu" → CaseDocuments

**web/src/components/cases/CaseDocuments.jsx**
- Button "Tạo văn bản" → gọi generate API
- Danh sách documents (Ant Design List)
- Mỗi item: icon + tên file + size + actions (Preview, Download)
- Button "Tải tất cả" → download ZIP

**web/src/components/cases/DocumentPreview.jsx**
- Ant Design Drawer (width: 800px)
- Render HTML preview trong iframe hoặc dangerouslySetInnerHTML
- Toolbar: Download, Print

**web/src/components/cases/SendEmailModal.jsx**
- Ant Design Modal
- Form: To, CC, Subject, Body (rich text), Attachments (checklist)
- Preview email trước khi gửi
- Submit → API call → success toast

**web/src/components/cases/DeliveryModal.jsx**
- Chọn delivery contact (Select từ API)
- Nhập tracking number
- Submit

### Verification
1. Generate documents → files created
2. Document list hiển thị đúng
3. Preview renders HTML
4. Download single file + ZIP
5. Send email thành công
6. Delivery info saved
```

---

## PROMPT — PHASE 5: Entry Form + OCR

```
Tiếp tục dự án chuyển đổi Streamlit → Flask + React SPA.

## Context
- Đây là trang "Nhập hồ sơ" — upload file → AI OCR → điền form → lưu.
- Views hiện tại: views/entry.py, views/entry_form.py (473 dòng), views/entry_viewer.py (266 dòng), views/entry_actions.py (409 dòng)
- Backend modules (giữ nguyên):
  - src/gemini_extractor.py: extract_fields() — Gemini AI extraction
  - src/ocr_accumulator.py: accumulate extractions
  - src/extractor.py: orchestrate extraction
  - src/preview.py: render PDF pages as images
  - src/image_annotator.py: annotate images
  - src/excel_writer.py: load_dropdown_options(), fill_template()

## Nhiệm vụ Phase 5

### 1. Flask Blueprint (api/blueprints/entry.py)

**POST /api/entry/upload**
- Multipart upload: multiple PDF/image files
- Lưu files vào data/uploads/
- Convert PDF pages thành images (dùng PyMuPDF)
- Response: { "upload_id": "uuid", "files": [{ "name": "doc.pdf", "pages": 3, "thumbnails": ["/api/entry/uploads/uuid/page_1.jpg"] }] }

**GET /api/entry/uploads/:upload_id/page/:page_num**
- Query params: rotation (0, 90, 180, 270)
- Response: image file (JPEG)

**POST /api/entry/extract**
Body: { "upload_id": "uuid", "pages": [1, 2, 3], "provider": "gemini", "model": "gemini-2.5-flash" }
- Chạy AI extraction (có thể lâu 10-30s)
- Response: { "extraction": { "customer_info": "Nguyễn Văn A", "address": "...", "so_thua": "123" } }
- Hoặc dùng SSE (Server-Sent Events) để stream progress nếu multi-page

**GET /api/entry/form-options**
- Response: dropdown options từ Excel template
- Logic: excel_writer.load_dropdown_options(excel_template_path)
- Response: { "branch": ["CN A", "CN B"], "purpose": ["Vay vốn", "Mua bán"] }

**POST /api/entry/save**
Body: { "extraction": { "...all fields..." }, "case_type": "individual"|"organization" }
- Lưu vào cases.db (sqlite_store.upsert_case)
- Response: { "case_id": 123 }

**GET /api/entry/excel-download**
Query params: case data fields
- Tạo filled Excel từ template
- Response: Excel file download

### 2. React Components

**web/src/pages/Entry.jsx** — Container page
- Layout 2 columns: Viewer (left, 40%) + Form (right, 60%)
- Top bar: Upload button + action buttons

**web/src/components/entry/FileUploader.jsx**
- Ant Design Upload.Dragger
- Accept: .pdf, .png, .jpg, .jpeg, .webp
- Multiple files
- Upload progress bar
- After upload: hiển thị thumbnail list

**web/src/components/entry/PageViewer.jsx**
- Hiển thị page image từ API
- Controls: Previous/Next page, Zoom in/out, Rotate (90°)
- Page thumbnails strip bên trái
- Thumbnail click → switch page

**web/src/components/entry/OcrActions.jsx**
- Button "Trích xuất AI" (với icon Gemini)
- Progress indicator khi đang extract
- Result preview trước khi apply vào form
- Button "Áp dụng kết quả" → fill form

**web/src/components/entry/EntryForm.jsx**
- Ant Design Form (complex, 20+ fields)
- 2 tabs: "Thông tin KH & Hợp đồng" + "Thông tin tài sản"
- Tab 1:
  - Loại KH (Radio: Cá nhân / Tổ chức)
  - Tên KH, Tên KH 2 (input)
  - SĐT, CCCD (input)
  - Địa chỉ (textarea)
  - Số HĐ, Chi nhánh, Nguồn (input/select)
  - Phí TD, Phí thu, Tổng phí (number input, auto-format VND)
  - Tháng TH (date picker, month mode)
  - NV thẩm định (select)
- Tab 2:
  - Mô tả TS (textarea, multi-line)
  - Địa chỉ TS (input)
  - Số thửa, Số tờ, Diện tích (input)
  - Mục đích sử dụng (select)
  - Tỉnh/Huyện/Xã (cascading selects)
- Bottom: Button "Lưu hồ sơ" + "Tải Excel"
- Dropdown options loaded từ /api/entry/form-options
- Dynamic: Khi chọn Loại KH = "Tổ chức" → hiện thêm fields MST, Người đại diện

### Verification
1. Upload PDF → thumbnails generated
2. Page viewer: navigate, zoom, rotate
3. AI extraction: click → loading → results shown
4. Apply extraction → form fields filled
5. Manual edit form fields
6. Save → case created in DB
7. Download Excel → filled template
8. Dropdown options load correctly
9. Form validation (required fields)
```

---

## PROMPT — PHASE 6: Sobo View (Sơ bộ)

```
Tiếp tục dự án chuyển đổi Streamlit → Flask + React SPA.

## Context
- Trang "Sơ bộ" quản lý yêu cầu thẩm định sơ bộ.
- Guest users CHỈ thấy trang này.
- Views hiện tại: views/sobo_view.py (479 dòng)
- Data từ: database_manager.list_sobo_records(), database_manager.upsert_sobo_record()
- Sobo record fields: id, asset_type, asset_description, location_link, email_recipient, 
  status, bank_source, notes, telegram_chat_id, created_at, updated_at,
  outbound_message_id, gcn_files (JSON array of file paths)
- LƯU Ý: database_manager dùng async (aiosqlite), cần wrap trong asyncio.run() cho Flask sync context

## Nhiệm vụ Phase 6

### 1. Flask Blueprint (api/blueprints/sobo.py)

**GET /api/sobo**
Query params: search, status, page, size, sort, order
Response: { items: [sobo records], total, page, pages }
Logic: Dùng asyncio.run(database_manager.list_sobo_records(db_path, ...))

**GET /api/sobo/:id**
Response: full sobo record

**PUT /api/sobo/:id**
Body: { fields to update }

**DELETE /api/sobo/:id**

**GET /api/sobo/:id/files**
- Đọc gcn_files JSON array → list file info
Response: [{ filename, size, url: "/api/sobo/123/files/filename.pdf" }]

**GET /api/sobo/:id/files/:filename**
- Download single GCN file

**GET /api/sobo/:id/files/download-all**
- Download ZIP nếu multiple files

**POST /api/sobo/from-case/:case_id**
- Tạo sobo record từ existing case
- Logic: đọc case data → tạo sobo record

### 2. React Components

**web/src/pages/Sobo.jsx** — Container page
- Search bar + filter (status)
- Sobo table
- Click row → detail drawer

**web/src/components/sobo/SoboTable.jsx**
- Ant Design Table
- Columns: STT, Loại TS, Mô tả TS, Email nhận, Trạng thái, Ngày tạo, Thao tác
- Status tags with colors:
  - "Chờ gửi" → orange
  - "Đã gửi" → blue  
  - "Đã phản hồi" → green
  - "Hủy" → red
- Action: Xem chi tiết, Tải GCN, Sửa, Xóa

**web/src/components/sobo/SoboDetailDrawer.jsx**
- Ant Design Drawer (width 600px)
- Hiển thị full thông tin sobo
- GCN files list với download buttons
- Location link (nếu có) → clickable map link

**web/src/components/sobo/SoboEditModal.jsx**
- Ant Design Modal + Form
- Fields: Loại TS, Mô tả, Email nhận, Trạng thái, Ghi chú
- Save → PUT API

### Verification
1. Sobo list loads correctly
2. Search + filter hoạt động
3. Detail drawer hiển thị đầy đủ info
4. Download GCN files (single + ZIP)
5. Edit sobo → save → refresh
6. Delete sobo with confirm
7. Guest user: chỉ thấy trang Sobo, không thấy nav khác
```

---

## PROMPT — PHASE 7: Organizations + Delivery

```
Tiếp tục dự án chuyển đổi Streamlit → Flask + React SPA.

## Context
- Organizations: views/organizations_view.py (277 dòng)
  - CRUD tổ chức (tax_code, name, abbreviation, representative)
  - Merge 2 tổ chức
  - AI extract org info từ uploaded documents
- Delivery: views/delivery_view.py (221 dòng)
  - CRUD delivery contacts (short_name, full_details)
  - Editable table (st.data_editor)
- Backend: sqlite_store.list_organizations(), upsert_organization(), delete_organization(), merge_organizations()
  database_manager.list_delivery_contacts(), upsert_delivery_contact(), delete_delivery_contact()

## Nhiệm vụ Phase 7

### 1. Flask Blueprints

**api/blueprints/organizations.py:**

GET    /api/organizations?search=... → [{ id, tax_code, name, abbreviation, representative }]
POST   /api/organizations → Create org
PUT    /api/organizations/:id → Update org
DELETE /api/organizations/:id → Delete org
POST   /api/organizations/merge → { "source_id": 1, "target_id": 2 } → Merge source into target
POST   /api/organizations/ai-extract → Upload files → AI extract → [{ tax_code, name }]

**api/blueprints/delivery.py:**

GET    /api/delivery/contacts?search=... → [{ id, short_name, full_details }]
POST   /api/delivery/contacts → Create contact
PUT    /api/delivery/contacts/:id → Update
DELETE /api/delivery/contacts/:id → Delete

### 2. React Components

**web/src/pages/Organizations.jsx**
- Search bar + Add button
- Ant Design Table: MST, Tên, Viết tắt, Người đại diện, Thao tác
- Modal add/edit org
- Modal merge orgs (2 selects → preview → confirm merge)
- AI Extract section: Upload files → show extracted results in editable table → save

**web/src/pages/Delivery.jsx**
- Search bar + Add button
- Ant Design Table (editable cells — dùng Ant Design EditableTable pattern): Tên viết tắt, Chi tiết đầy đủ
- Inline edit: click cell → edit → blur to save
- Add row button
- Delete with confirm

### Verification
1. CRUD organizations
2. Merge 2 organizations → source deleted, target updated
3. AI extract from uploaded docs → org data extracted
4. CRUD delivery contacts
5. Inline edit delivery table
```

---

## PROMPT — PHASE 8: Templates + Settings

```
Tiếp tục dự án chuyển đổi Streamlit → Flask + React SPA.

## Context
- Templates: views/templates.py → template_list.py → template_editor.py → template_history.py
  - List Word templates (.docx) từ configured directories
  - Edit template (upload new version)
  - View placeholder list trong template
  - Version history
- Settings: views/settings.py (606 dòng)
  - Cấu hình đường dẫn (template dirs, output dir)
  - OAuth2 Google/Outlook connection
  - Backup/restore database
  - System toggles (auto-start services, etc.)
- Backend: 
  - src/template_manager.py: load_template_config(), save_template_config()
  - src/oauth2_service.py: load_oauth_config(), get_authorization_url(), exchange_code_for_tokens()
  - src/backup_service.py: create_backup()

## Nhiệm vụ Phase 8

### 1. Flask Blueprints

**api/blueprints/templates_bp.py:**

GET    /api/templates → [{ name, path, size, last_modified }]
  Logic: Scan configured template directories for .docx files
GET    /api/templates/:name → { name, content_preview, placeholders: ["{{customer_info}}"] }
PUT    /api/templates/:name → Upload new template version (multipart)
GET    /api/templates/:name/history → [{ version, modified_at, modified_by }]

**api/blueprints/settings.py:**

GET    /api/settings → {
  paths: { excel_template, individual_template_dir, organization_template_dir, output_dir },
  oauth: { google: { connected: true, email: "..." }, outlook: { connected: false } },
  services: { telegram: "running", mail_listener: "running", ngrok: "running" },
  system: { version: "2.0", db_size: "2MB" }
}

PUT    /api/settings/paths → Update path configurations
  Body: { excel_template_path, individual_template_dir }
  Logic: template_manager.save_template_config()

GET    /api/settings/oauth/:provider/auth-url → { url: "https://accounts.google.com/..." }
  Logic: oauth2_service.get_authorization_url(provider, redirect_uri)
  redirect_uri = frontend URL + /settings/oauth/callback

POST   /api/settings/oauth/callback → { provider, code }
  Logic: oauth2_service.exchange_code_for_tokens(provider, code, redirect_uri)

DELETE /api/settings/oauth/:provider → Disconnect OAuth
  Logic: Remove tokens from oauth_config.json

POST   /api/settings/backup → Create backup
  Response: { "backup_path": "data/backups/backup_20260620.zip" }
  
GET    /api/settings/backup/download → Download backup ZIP

POST   /api/settings/backup/restore → Upload backup ZIP → restore
  Multipart: backup.zip file

### 2. React Components

**web/src/pages/Templates.jsx**
- Template list table (Ant Design Table)
- Click → TemplateEditor drawer/page
- Upload new template

**web/src/components/templates/TemplateEditor.jsx**
- Template info: name, path, size
- Placeholder list (read-only, Ant Design Tag list)
- Upload new version (drag & drop)
- Version history list (Ant Design Timeline)

**web/src/pages/Settings.jsx**
- Ant Design Tabs: Đường dẫn | OAuth2 | Sao lưu | Hệ thống

- Tab "Đường dẫn": Ant Design Form với 4 path inputs + Save button
- Tab "OAuth2": 
  - Google card: status (connected/disconnected) + Connect/Disconnect button
  - Outlook card: status + Connect/Disconnect button
  - Connect → redirect to OAuth URL → callback → show success
- Tab "Sao lưu":
  - Button "Tạo bản sao lưu" → download ZIP
  - Upload area "Khôi phục" → upload ZIP → confirm → restore
- Tab "Hệ thống":
  - System info cards (version, DB size, uptime)
  - Service status (Telegram, Mail Listener, Ngrok) với on/off indicators

### OAuth2 Callback Flow
- Settings page có button "Kết nối Google"
- Click → GET /api/settings/oauth/google/auth-url → nhận URL
- Redirect user tới Google consent screen
- Google redirects back to: http://localhost:5173/settings?code=xxx&state=google
- Settings page detect query params → POST /api/settings/oauth/callback
- Show success message

### Verification
1. Template list loads
2. Template editor shows placeholders
3. Upload new template version
4. OAuth2 Google connect flow
5. OAuth2 Outlook connect flow
6. Disconnect OAuth
7. Create backup → download ZIP
8. Restore backup from ZIP
9. Path settings save
```

---

## PROMPT — PHASE 9: Integration & Polish

```
Tiếp tục dự án chuyển đổi Streamlit → Flask + React SPA.

## Context
- Tất cả pages đã hoạt động (Phase 1-8 hoàn thành).
- Cần: tích hợp orchestration, deployment, testing, UI polish.

## Nhiệm vụ Phase 9

### 1. Cập nhật Main Orchestrator (main.py)

Sửa main.py để chạy Flask thay Streamlit:
- Thay run_streamlit() → run_flask():
```python
async def run_flask() -> None:
    port = os.getenv("FLASK_PORT", "5000")
    await run_subprocess(
        "flask",
        [sys.executable, "-m", "api.run", "--port", port],
    )
```
- Giữ nguyên run_telegram_webhook() và run_mail_listener()
- Tasks: [flask, telegram, mail_listener]

### 2. Cập nhật background_services.py

Thay start_streamlit_if_enabled() → start_flask_if_enabled():
- Command: [sys.executable, "-m", "api.run"]
- PID file: flask.pid
- Log files: flask_stdout.log, flask_stderr.log

### 3. Production Build

**React build:**
```bash
cd web
npm run build  # Output: web/dist/
```

**Flask serve static:**
Cấu hình Flask serve React static files trong production:
```python
# api/__init__.py
from pathlib import Path
from flask import send_from_directory

if not app.debug:
    static_dir = str(Path(__file__).parent.parent / "web" / "dist")
    
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_react(path):
        full_path = Path(static_dir) / path
        if path and full_path.exists():
            return send_from_directory(static_dir, path)
        return send_from_directory(static_dir, "index.html")
```

**Hoặc Nginx config (khuyến nghị cho production):**
```nginx
server {
    listen 80;
    server_name thamdinh.example.com;

    # React SPA
    location / {
        root /path/to/web/dist;
        try_files $uri $uri/ /index.html;
    }

    # Flask API
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Telegram webhook
    location /webhook/ {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

### 4. Docker Compose (optional)

```yaml
version: "3.8"
services:
  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    ports:
      - "5000:5000"
    volumes:
      - ./data:/app/data
    env_file: API.env

  web:
    build:
      context: ./web
      dockerfile: Dockerfile.web
    ports:
      - "80:80"
    depends_on:
      - api

  telegram:
    build:
      context: .
      dockerfile: Dockerfile.api
    command: python -m uvicorn src.telegram_server:app --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    env_file: API.env
```

### 5. Cập nhật batch scripts

**KhoiDongHeThong.bat** — thay streamlit commands → flask:
```bat
start "Flask API" cmd /k "python -m api.run"
start "React" cmd /k "cd web && npm run dev"
```

**Tạo build_production.bat:**
```bat
cd web && npm run build
echo Production build complete. Run: python -m api.run
```

### 6. UI Polish

- Loading skeletons cho tables và cards (Ant Design Skeleton)
- Error boundary component (catch React errors → friendly error page)
- Empty states cho tables/lists (Ant Design Empty)
- Breadcrumbs cho nested pages (/cases/:id)
- Keyboard shortcuts:
  - Ctrl+K → global search
  - Escape → close modal
- Toast notifications consistency (Ant Design message)
- Dark mode toggle (Ant Design theme switching) — optional
- Print-friendly styles cho document preview
- Mobile responsive:
  - Hamburger menu for nav
  - Stacked layout for forms
  - Swipeable tabs

### 7. Testing

**API Integration Tests (pytest):**
```bash
# Tạo tests/test_api/
pytest tests/test_api/ -v
```

Test checklist:
- Test tất cả endpoints với test database
- Test auth flow (login → access → logout)
- Test CRUD operations cho mỗi resource
- Test file upload/download
- Test error cases (404, 401, validation errors)

**Frontend (optional):**
```bash
cd web
npm install -D vitest @testing-library/react
npm run test
```

### 8. Data Migration Verification

- Verify existing data/cases.db works với Flask API
- Verify existing data/telegram_records.db works
- Verify OAuth2 tokens still valid
- Verify uploaded files accessible
- Verify template files accessible

### 9. Cleanup

- Cập nhật README.md với hướng dẫn mới
- Cập nhật .gitignore (thêm web/node_modules, web/dist)
- Cập nhật CaiDat.bat (thêm npm install)
- KHÔNG xóa code Streamlit cũ — để fallback

### Verification Checklist Tổng Thể
1. [ ] Flask API start OK
2. [ ] React dev server start OK  
3. [ ] Login/logout flow
4. [ ] Dashboard: KPI, charts, filters
5. [ ] Cases: CRUD, table, filter, sort, pagination
6. [ ] Case documents: generate, preview, download, email
7. [ ] Entry: upload, OCR, form, save
8. [ ] Sobo: list, detail, edit, download
9. [ ] Organizations: CRUD, merge, AI extract
10. [ ] Delivery: CRUD, inline edit
11. [ ] Templates: list, edit, history
12. [ ] Settings: paths, OAuth2, backup/restore
13. [ ] Guest user: only sees Sobo
14. [ ] Production build works
15. [ ] Nginx proxy config works
16. [ ] All background services (Telegram, Mail, Ngrok) still work
17. [ ] Mobile responsive
18. [ ] Error handling (404, 500, network errors)
```

---

## Tổng kết thứ tự thực hiện

```
Phase 0 (2-3 ngày)  →  Phase 1 (2 ngày)  →  ┬─ Phase 2 (3 ngày)
                                               ├─ Phase 3 (5-6 ngày) → Phase 4 (4 ngày)
                                               ├─ Phase 5 (4-5 ngày)
                                               ├─ Phase 6 (3 ngày)
                                               ├─ Phase 7 (3 ngày)
                                               └─ Phase 8 (3 ngày)
                                                          ↓
                                              Phase 9 (4-5 ngày) — sau khi tất cả xong
```

> **Tổng: 35-45 ngày** cho 1 developer. Có thể rút ngắn còn **20-25 ngày** nếu 2 developer chạy song song Phase 2-8.
