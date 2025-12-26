from app import create_app, db, models
from app.models import User, Customer, Employee, WarehouseStaff, Package, TrackingEvent, Bill, UserRole, CustomerType, PricingRule, DeliverySpeed

app = create_app()

with app.app_context():
    print("=== 開始完整重置 (Full System Reset) ===")
    
    # 1. 刪除所有資料表並重建 (Drop and Recreate All Tables)
    # 這是最乾淨的方法，確保沒有殘留的外鍵約束問題
    print("正在刪除資料庫架構...")
    db.drop_all()
    print("正在重建資料庫架構...")
    db.create_all()
    print("資料庫重置完成。")

    # 2. 重新初始化定價規則 (Re-initialize Pricing Rules)
    print("正在初始化定價規則...")
    rules = [
        PricingRule(service_type=DeliverySpeed.OVERNIGHT, base_rate=150.0, rate_per_kg=20.0),
        PricingRule(service_type=DeliverySpeed.TWO_DAY, base_rate=100.0, rate_per_kg=15.0),
        PricingRule(service_type=DeliverySpeed.STANDARD, base_rate=60.0, rate_per_kg=10.0),
        PricingRule(service_type=DeliverySpeed.ECONOMY, base_rate=40.0, rate_per_kg=5.0),
    ]
    db.session.add_all(rules)
    print("定價規則建立完成。")

    # 3. 創建標準帳號 (Create Standard Accounts)
    print("正在建立標準帳號...")
    
    users = []

    # 1. 一般客戶 (General Customer)
    u_customer = Customer(
        username='customer', 
        full_name='王小明', 
        email='customer@test.com', 
        phone='0900111111', 
        address='台北市信義區信義路一段1號',
        role=UserRole.CUSTOMER, 
        customer_type=CustomerType.NON_CONTRACT
    )
    u_customer.set_password('123456')
    users.append(u_customer)

    # 2. 合約客戶 (Contract Customer)
    u_contract = Customer(
        username='contract', 
        full_name='陳大明', 
        email='contract@test.com', 
        phone='0900222222', 
        address='台北市大安區和平東路二段2號',
        role=UserRole.CUSTOMER, 
        customer_type=CustomerType.CONTRACT,
        balance=1000.0  # 月結帳戶初始餘額
    )
    u_contract.set_password('123456')
    users.append(u_contract)

    # 3. 預付客戶 (Prepaid Customer) - NEW
    u_prepaid = Customer(
        username='prepaid',
        full_name='預付小弟',
        email='prepaid@test.com',
        phone='0900999999',
        address='新竹科學園區力行六路1號',
        role=UserRole.CUSTOMER,
        customer_type=CustomerType.PREPAID,
        balance=0.0,
        prepaid_by='台灣積體電路股份製造有限公司'
    )
    u_prepaid.set_password('123456')
    users.append(u_prepaid)

    # 3. 客服人員 (Customer Service)
    u_cs = Employee(
        username='cs', 
        full_name='客服人員 (Service)', 
        email='cs@test.com', 
        phone='0900333333', 
        role=UserRole.CS, 
        department='客服部'
    )
    u_cs.set_password('123456')
    users.append(u_cs)

    # 4. 管理員 (Admin)
    u_admin = Employee(
        username='admin', 
        full_name='管理員 (Admin)', 
        email='admin@test.com', 
        phone='0900444444', 
        role=UserRole.ADMIN, 
        department='管理部'
    )
    u_admin.set_password('123456')
    users.append(u_admin)

    # 5. 司機 (Driver)
    u_driver = Employee(
        username='driver', 
        full_name='司機 (Driver)', 
        email='driver@test.com', 
        phone='0900555555', 
        role=UserRole.DRIVER, 
        department='物流部'
    )
    u_driver.set_password('123456')
    users.append(u_driver)

    # 6. 倉儲人員 (Warehouse)
    u_warehouse = WarehouseStaff(
        username='warehouse', 
        full_name='倉儲人員 (Warehouse)', 
        email='warehouse@test.com', 
        phone='0900666666', 
        role=UserRole.WAREHOUSE, 
        department='倉儲部',
        warehouse_location_id='WH-TAIPEI-01'
    )
    u_warehouse.set_password('123456')
    users.append(u_warehouse)

    db.session.add_all(users)
    db.session.commit()

    print("\n=== 重置與帳號建立詳情 ===")
    print("所有帳號密碼皆為: 123456")
    print("--------------------------------------------------")
    print(f"{'角色 (Role)':<15} | {'帳號 (Username)':<15} | {'名稱 (Name)'}")
    print("--------------------------------------------------")
    for u in users:
        role_name = u.role.value if hasattr(u, 'role') else ''
        if role_name == 'customer':
            role_name = f"{u.customer_type.name}"
        print(f"{role_name:<15} | {u.username:<15} | {u.full_name}")
    print("--------------------------------------------------")
