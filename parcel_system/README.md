# 物流追蹤系統 (Parcel Tracking System)

這是一個基於 Flask 的物流追蹤與計費系統。

## 系統需求

- Python 3.8+
- Flask
- SQLAlchemy

## 安裝步驟

1. 安裝依賴套件：
   ```bash
   pip install -r requirements.txt
   ```

## 系統初始化

在首次執行或需要重置資料庫時，請執行以下指令：

```bash
python reinit_users.py
```

此指令會：
1. 清除並重建資料庫
2. 初始化定價規則
3. 建立預設測試帳號

## 啟動系統

執行以下指令啟動網頁伺服器：

```bash
python run.py
```

系統將在預設瀏覽器中開啟 (通常是 http://127.0.0.1:5000)。

## 測試帳號列表

所有帳號的預設密碼皆為：`123456`

| 角色 (Role) | 帳號 (Username) | 名稱 | 備註 |
|------------|----------------|------|------|
| 一般客戶 | customer | 一般客戶 (Customer) | 非合約客戶 |
| 預付客戶 | prepaid | 預付客戶 (Prepaid) | 預付客戶 |
| 合約客戶 | contract | 合約客戶 (Contract) | 月結客戶 |
| 客服人員 | cs | 客服人員 (Service) | 客服部 |
| 管理員 | admin | 管理員 (Admin) | 管理部 |
| 司機 | driver | 司機 (Driver) | 物流部 |
| 倉儲人員 | warehouse | 倉儲人員 (Warehouse) | 倉儲部 (台北一倉) |
