# 包裹追蹤與計費系統 (Parcel Tracking and Billing System) - 實作計畫

## 1. 專案規劃 (Project Planning)
本專案旨在開發一套基於 Python 的包裹追蹤與計費系統，滿足物流公司的核心業務需求。

### 技術堆疊 (Technology Stack)
- **後端語言**: Python 3.x
- **Web 框架**: Flask (輕量級，適合快速開發與展示)
- **資料庫 ORM**: SQLAlchemy (對應類別圖結構)
- **資料庫**: SQLite (開發用，易於攜帶與設置)
- **前端**: HTML5, Vanilla CSS3 (現代化設計), Vanilla JavaScript
- **測試框架**: pytest (單元測試)

### 開發階段 (Development Phases)
1.  **系統建模與資料庫設計**: 根據類別圖建立 Python Models (`models.py`)。
2.  **核心業務邏輯實作**: 實作客戶管理、包裹建立、追蹤事件記錄、計費邏輯 (`services.py`)。
3.  **Web 介面開發**:
    - 設計現代化、響應式的 UI (繁體中文)。
    - 實作各角色 (客戶、司機、管理員) 的操作介面。
4.  **測試與驗證**: 撰寫單元測試 (`tests/`) 確保功能正確性。
5.  **文件與報告產出**: 整理專案報告所需的各項說明。

## 2. 系統架構 (System Architecture)
採用 MVC (Model-View-Controller) 架構模式：
- **Model**: 定義資料結構 (User, Package, TrackingEvent 等)。
- **View**: 前端 HTML 模板，負責展示資料。
- **Controller**: Flask Routes，處理使用者請求並呼叫業務邏輯。

## 3. 待辦事項 (Task List)
- [ ] 初始化專案結構與環境設定 (`requirements.txt`)
- [x] 實作資料庫模型 (`app/models.py`) - **優先**
- [x] 實作核心服務邏輯 (`app/services.py`)
- [x] 建立 Web 應用程式入口 (`run.py`, `app/__init__.py`)
- [x] 設計前端樣式 (`app/static/css/style.css`) - **需符合現代美學**
- [x] 實作主要頁面 (首頁, 追蹤頁, 登入頁, 後台管理)
- [ ] 撰寫測試案例 (`tests/test_core.py`)
