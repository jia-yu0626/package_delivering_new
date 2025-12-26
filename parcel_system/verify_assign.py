from app import create_app, db, models, services

app = create_app()
with app.app_context():
    # 1. 確保至少有一位司機
    driver = db.session.execute(
        db.select(models.User).filter_by(role=models.UserRole.DRIVER)
    ).scalar_one_or_none()
    
    if not driver:
        print("錯誤：資料庫中沒有司機，請先執行 add_users.py")
        exit()

    # 2. 建立一個狀態為 SORTING 且未分配的測試包裹
    # (或手動將現有包裹狀態改為 SORTING)
    test_pkg = db.session.execute(
        db.select(models.Package).filter_by(status=models.PackageStatus.SORTING, assigned_driver_id=None)
    ).scalars().first()

    if not test_pkg:
        print("沒有符合條件的包裹，請建立一個狀態為 SORTING 的包裹")
    else:
        # 3. 執行自動分配
        count = services.auto_assign_packages()
        print(f"成功分配了 {count} 個包裹")

        # 4. 檢查結果
        db.session.refresh(test_pkg)
        print(f"包裹 {test_pkg.tracking_number} 現在指派給司機 ID: {test_pkg.assigned_driver_id}")