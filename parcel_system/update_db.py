# 更新資料庫結構 - 新增 audit_logs 表格
from app import create_app, db
from app.models import AuditLog

app = create_app()

with app.app_context():
    # 只建立新的表格，不影響現有資料
    db.create_all()
    print("資料庫已更新，audit_logs 表格已建立！")
