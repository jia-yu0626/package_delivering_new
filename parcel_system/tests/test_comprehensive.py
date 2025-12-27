"""
綜合測試案例 (Comprehensive Test Cases)
測試包裹追蹤與計費系統的所有核心功能

測試涵蓋範圍:
1. 使用者模型 (User Models) - 各種角色的建立和驗證
2. 包裹服務 (Package Services) - 建立、追蹤、更新
3. 計費功能 (Billing) - 各種付款方式
4. 倉儲功能 (Warehouse) - 包裹處理和異常回報
5. 司機派送 (Driver Delivery) - 自動分配和派送流程
6. 搜尋功能 (Search) - 使用者和包裹搜尋
7. 定價規則 (Pricing Rules) - CRUD 操作
8. 系統日誌 (Audit Logs) - 操作記錄
"""

import pytest
from datetime import datetime, timedelta
from app import create_app, db, models, services
from app.models import (
    UserRole, CustomerType, PackageStatus, PackageType, 
    DeliverySpeed, PaymentMethod, PACKAGE_STATUS_LABELS
)


# ===== 測試前置設定 (Fixtures) =====

@pytest.fixture
def app():
    """建立測試用 Flask 應用程式"""
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False
    })
    
    with app.app_context():
        db.create_all()
        # 初始化定價規則
        pricing_rules = [
            models.PricingRule(service_type=DeliverySpeed.OVERNIGHT, base_rate=150.0, rate_per_kg=20.0),
            models.PricingRule(service_type=DeliverySpeed.TWO_DAY, base_rate=100.0, rate_per_kg=15.0),
            models.PricingRule(service_type=DeliverySpeed.STANDARD, base_rate=60.0, rate_per_kg=10.0),
            models.PricingRule(service_type=DeliverySpeed.ECONOMY, base_rate=40.0, rate_per_kg=5.0),
        ]
        db.session.add_all(pricing_rules)
        db.session.commit()
        
        yield app
        
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """建立測試客戶端"""
    return app.test_client()


@pytest.fixture
def sample_customer(app):
    """建立範例客戶"""
    with app.app_context():
        customer = models.Customer(
            username="sample_customer",
            full_name="範例客戶",
            email="sample@example.com",
            phone="0912345678",
            role=UserRole.CUSTOMER,
            customer_type=CustomerType.NON_CONTRACT
        )
        customer.set_password("password123")
        db.session.add(customer)
        db.session.commit()
        return customer.id


@pytest.fixture
def sample_driver(app):
    """建立範例司機"""
    with app.app_context():
        driver = models.Driver(
            username="driver01",
            full_name="測試司機",
            email="driver01@example.com",
            phone="0923456789",
            role=UserRole.DRIVER,
            department="物流部",
            vehicle_id="ABC-1234"
        )
        driver.set_password("driver123")
        db.session.add(driver)
        db.session.commit()
        return driver.id


@pytest.fixture
def sample_warehouse_staff(app):
    """建立範例倉儲人員"""
    with app.app_context():
        wh_staff = models.WarehouseStaff(
            username="warehouse01",
            full_name="倉儲人員一號",
            email="wh01@example.com",
            phone="0934567890",
            role=UserRole.WAREHOUSE,
            department="倉儲部",
            warehouse_location_id="WH-TAIPEI-001"
        )
        wh_staff.set_password("warehouse123")
        db.session.add(wh_staff)
        db.session.commit()
        return wh_staff.id


# ===== 1. 使用者模型測試 (User Model Tests) =====

class TestUserModels:
    """測試使用者模型相關功能"""

    def test_create_customer(self, app):
        """測試建立一般客戶"""
        with app.app_context():
            customer = models.Customer(
                username="test_customer",
                full_name="測試客戶",
                email="test@test.com",
                phone="0911111111",
                role=UserRole.CUSTOMER,
                customer_type=CustomerType.NON_CONTRACT
            )
            customer.set_password("test123")
            db.session.add(customer)
            db.session.commit()
            
            saved = db.session.get(models.Customer, customer.id)
            assert saved is not None
            assert saved.username == "test_customer"
            assert saved.check_password("test123")
            assert not saved.check_password("wrong_password")
            assert saved.customer_type == CustomerType.NON_CONTRACT

    def test_create_contract_customer(self, app):
        """測試建立合約客戶"""
        with app.app_context():
            customer = models.Customer(
                username="contract_customer",
                full_name="合約客戶",
                email="contract@company.com",
                phone="0922222222",
                role=UserRole.CUSTOMER,
                customer_type=CustomerType.CONTRACT,
                billing_preference=PaymentMethod.MONTHLY
            )
            customer.set_password("contract123")
            db.session.add(customer)
            db.session.commit()
            
            saved = db.session.get(models.Customer, customer.id)
            assert saved.customer_type == CustomerType.CONTRACT
            assert saved.billing_preference == PaymentMethod.MONTHLY
            assert saved.type_label == "合約客戶"

    def test_create_prepaid_customer(self, app):
        """測試建立預付客戶"""
        with app.app_context():
            customer = models.Customer(
                username="prepaid_customer",
                full_name="預付客戶",
                email="prepaid@test.com",
                phone="0933333333",
                role=UserRole.CUSTOMER,
                customer_type=CustomerType.PREPAID,
                balance=1000.0,
                prepaid_by="測試公司"
            )
            customer.set_password("prepaid123")
            db.session.add(customer)
            db.session.commit()
            
            saved = db.session.get(models.Customer, customer.id)
            assert saved.customer_type == CustomerType.PREPAID
            assert saved.balance == 1000.0
            assert saved.prepaid_by == "測試公司"
            assert saved.type_label == "預付客戶"

    def test_create_driver(self, app, sample_driver):
        """測試建立司機"""
        with app.app_context():
            driver = db.session.get(models.Driver, sample_driver)
            assert driver is not None
            assert driver.role == UserRole.DRIVER
            assert driver.vehicle_id == "ABC-1234"

    def test_create_warehouse_staff(self, app, sample_warehouse_staff):
        """測試建立倉儲人員"""
        with app.app_context():
            wh = db.session.get(models.WarehouseStaff, sample_warehouse_staff)
            assert wh is not None
            assert wh.role == UserRole.WAREHOUSE
            assert wh.warehouse_location_id == "WH-TAIPEI-001"

    def test_create_admin(self, app):
        """測試建立管理員"""
        with app.app_context():
            admin = models.Employee(
                username="admin01",
                full_name="系統管理員",
                email="admin@system.com",
                phone="0944444444",
                role=UserRole.ADMIN,
                department="IT部門"
            )
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()
            
            saved = db.session.get(models.Employee, admin.id)
            assert saved.role == UserRole.ADMIN

    def test_create_cs_staff(self, app):
        """測試建立客服人員"""
        with app.app_context():
            cs = models.Employee(
                username="cs01",
                full_name="客服專員",
                email="cs@service.com",
                phone="0955555555",
                role=UserRole.CS,
                department="客服部"
            )
            cs.set_password("cs123")
            db.session.add(cs)
            db.session.commit()
            
            saved = db.session.get(models.Employee, cs.id)
            assert saved.role == UserRole.CS


# ===== 2. 包裹服務測試 (Package Services Tests) =====

class TestPackageServices:
    """測試包裹服務相關功能"""

    def test_generate_tracking_number(self, app):
        """測試追蹤號碼生成"""
        with app.app_context():
            tn1 = services.generate_tracking_number()
            tn2 = services.generate_tracking_number()
            
            assert tn1.startswith("TW-")
            assert tn2.startswith("TW-")
            assert tn1 != tn2  # 確保唯一性

    def test_create_package_standard(self, app, sample_customer):
        """測試建立標準包裹"""
        with app.app_context():
            recipient_data = {
                'name': '收件人測試',
                'address': '台北市信義區',
                'phone': '0987654321'
            }
            package_data = {
                'weight': 2.5,
                'width': 20,
                'height': 15,
                'length': 30,
                'package_type': 'MEDIUM_BOX',
                'delivery_speed': 'STANDARD'
            }
            
            pkg = services.create_package(sample_customer, recipient_data, package_data)
            
            assert pkg is not None
            assert pkg.tracking_number.startswith("TW-")
            assert pkg.status == PackageStatus.CREATED
            assert pkg.weight == 2.5
            assert pkg.shipping_cost == 85.0  # 60 + 2.5*10

    def test_create_package_overnight(self, app, sample_customer):
        """測試建立隔夜達包裹"""
        with app.app_context():
            pkg = services.create_package(
                sample_customer,
                {'name': 'R', 'address': 'A', 'phone': 'P'},
                {'weight': 3.0, 'width': 10, 'height': 10, 'length': 10, 
                 'package_type': 'SMALL_BOX', 'delivery_speed': 'OVERNIGHT'}
            )
            
            assert pkg.delivery_speed == DeliverySpeed.OVERNIGHT
            assert pkg.shipping_cost == 210.0  # 150 + 3*20
            assert pkg.delivery_speed_label == "隔夜達"

    def test_create_package_economy(self, app, sample_customer):
        """測試建立經濟速遞包裹"""
        with app.app_context():
            pkg = services.create_package(
                sample_customer,
                {'name': 'R', 'address': 'A', 'phone': 'P'},
                {'weight': 5.0, 'width': 10, 'height': 10, 'length': 10,
                 'package_type': 'SMALL_BOX', 'delivery_speed': 'ECONOMY'}
            )
            
            assert pkg.delivery_speed == DeliverySpeed.ECONOMY
            assert pkg.shipping_cost == 65.0  # 40 + 5*5
            assert pkg.delivery_speed_label == "經濟速遞"

    def test_create_package_validation_negative_weight(self, app, sample_customer):
        """測試包裹建立驗證 - 負數重量"""
        with app.app_context():
            with pytest.raises(ValueError, match="重量與尺寸必須大於 0"):
                services.create_package(
                    sample_customer,
                    {'name': 'R', 'address': 'A', 'phone': 'P'},
                    {'weight': -1.0, 'width': 10, 'height': 10, 'length': 10,
                     'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'}
                )

    def test_create_package_validation_zero_dimension(self, app, sample_customer):
        """測試包裹建立驗證 - 零尺寸"""
        with app.app_context():
            with pytest.raises(ValueError):
                services.create_package(
                    sample_customer,
                    {'name': 'R', 'address': 'A', 'phone': 'P'},
                    {'weight': 1.0, 'width': 0, 'height': 10, 'length': 10,
                     'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'}
                )

    def test_create_package_with_special_flags(self, app, sample_customer):
        """測試建立包含特殊標記的包裹"""
        with app.app_context():
            pkg = services.create_package(
                sample_customer,
                {'name': 'R', 'address': 'A', 'phone': 'P'},
                {'weight': 1.0, 'width': 10, 'height': 10, 'length': 10,
                 'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD',
                 'is_fragile': True, 'is_hazardous': True, 'is_international': True,
                 'declared_value': 5000.0, 'content_description': '易碎物品'}
            )
            
            assert pkg.is_fragile == True
            assert pkg.is_hazardous == True
            assert pkg.is_international == True
            assert pkg.declared_value == 5000.0
            assert pkg.content_description == '易碎物品'

    def test_get_package_by_tracking(self, app, sample_customer):
        """測試依追蹤號碼查詢包裹"""
        with app.app_context():
            pkg = services.create_package(
                sample_customer,
                {'name': 'R', 'address': 'A', 'phone': 'P'},
                {'weight': 1.0, 'width': 10, 'height': 10, 'length': 10,
                 'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'}
            )
            
            found = services.get_package_by_tracking(pkg.tracking_number)
            assert found is not None
            assert found.id == pkg.id

    def test_get_package_by_tracking_not_found(self, app):
        """測試查詢不存在的追蹤號碼"""
        with app.app_context():
            found = services.get_package_by_tracking("TW-NOTEXIST")
            assert found is None

    def test_get_user_packages(self, app, sample_customer):
        """測試查詢使用者的所有包裹"""
        with app.app_context():
            # 建立多個包裹
            for i in range(3):
                services.create_package(
                    sample_customer,
                    {'name': f'R{i}', 'address': f'A{i}', 'phone': f'P{i}'},
                    {'weight': 1.0, 'width': 10, 'height': 10, 'length': 10,
                     'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'}
                )
            
            packages = services.get_user_packages(sample_customer)
            assert len(packages) == 3


# ===== 3. 追蹤事件測試 (Tracking Events Tests) =====

class TestTrackingEvents:
    """測試包裹追蹤事件"""

    def test_add_tracking_event(self, app, sample_customer):
        """測試新增追蹤事件"""
        with app.app_context():
            pkg = services.create_package(
                sample_customer,
                {'name': 'R', 'address': 'A', 'phone': 'P'},
                {'weight': 1.0, 'width': 10, 'height': 10, 'length': 10,
                 'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'}
            )
            
            # 初始狀態應有一個 CREATED 事件
            assert len(pkg.tracking_events) == 1
            assert pkg.tracking_events[0].status == PackageStatus.CREATED
            
            # 新增 PICKED_UP 事件
            result = services.add_tracking_event(
                pkg.tracking_number, "PICKED_UP", "台北站", "司機已取件"
            )
            assert result == True
            
            # 重新查詢確認
            updated_pkg = services.get_package_by_tracking(pkg.tracking_number)
            assert updated_pkg.status == PackageStatus.PICKED_UP
            assert len(updated_pkg.tracking_events) == 2

    def test_full_tracking_flow(self, app, sample_customer):
        """測試完整的追蹤流程"""
        with app.app_context():
            pkg = services.create_package(
                sample_customer,
                {'name': 'R', 'address': 'A', 'phone': 'P'},
                {'weight': 1.0, 'width': 10, 'height': 10, 'length': 10,
                 'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'}
            )
            
            # 完整的物流流程
            statuses = [
                ("PICKED_UP", "起運地", "司機已取件"),
                ("IN_TRANSIT", "幹線", "運輸中"),
                ("SORTING", "台北分揀中心", "分揀處理"),
                ("OUT_FOR_DELIVERY", "末端配送站", "派送中"),
                ("DELIVERED", "收件地址", "已送達簽收")
            ]
            
            for status, location, description in statuses:
                services.add_tracking_event(pkg.tracking_number, status, location, description)
            
            final_pkg = services.get_package_by_tracking(pkg.tracking_number)
            assert final_pkg.status == PackageStatus.DELIVERED
            assert len(final_pkg.tracking_events) == 6  # 1 CREATED + 5 updates
            assert final_pkg.status_label == "已送達"

    def test_tracking_event_with_user(self, app, sample_customer, sample_driver):
        """測試包含操作人員的追蹤事件"""
        with app.app_context():
            pkg = services.create_package(
                sample_customer,
                {'name': 'R', 'address': 'A', 'phone': 'P'},
                {'weight': 1.0, 'width': 10, 'height': 10, 'length': 10,
                 'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'}
            )
            
            services.add_tracking_event(
                pkg.tracking_number, "PICKED_UP", "取件點", "已取件",
                user_id=sample_driver
            )
            
            updated_pkg = services.get_package_by_tracking(pkg.tracking_number)
            latest_event = updated_pkg.tracking_events[-1]
            assert latest_event.handled_by_id == sample_driver

    def test_tracking_event_exception(self, app, sample_customer):
        """測試異常狀態追蹤"""
        with app.app_context():
            pkg = services.create_package(
                sample_customer,
                {'name': 'R', 'address': 'A', 'phone': 'P'},
                {'weight': 1.0, 'width': 10, 'height': 10, 'length': 10,
                 'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'}
            )
            
            # 測試各種異常狀態
            services.add_tracking_event(pkg.tracking_number, "EXCEPTION", "異常地點", "無法聯繫收件人")
            pkg = services.get_package_by_tracking(pkg.tracking_number)
            assert pkg.status == PackageStatus.EXCEPTION
            assert pkg.status_label == "異常狀況"

    def test_status_labels(self):
        """測試狀態標籤中文對應"""
        assert PACKAGE_STATUS_LABELS[PackageStatus.CREATED] == "已建立"
        assert PACKAGE_STATUS_LABELS[PackageStatus.PICKED_UP] == "起運地收件"
        assert PACKAGE_STATUS_LABELS[PackageStatus.IN_TRANSIT] == "運輸至物流中心"
        assert PACKAGE_STATUS_LABELS[PackageStatus.SORTING] == "分揀中"
        assert PACKAGE_STATUS_LABELS[PackageStatus.OUT_FOR_DELIVERY] == "派送中"
        assert PACKAGE_STATUS_LABELS[PackageStatus.DELIVERED] == "已送達"
        assert PACKAGE_STATUS_LABELS[PackageStatus.LOST] == "遺失包裹"
        assert PACKAGE_STATUS_LABELS[PackageStatus.DAMAGED] == "包裹損毀"


# ===== 4. 計費功能測試 (Billing Tests) =====

class TestBilling:
    """測試計費相關功能"""

    def test_calculate_shipping_cost_standard(self, app):
        """測試標準速遞運費計算"""
        with app.app_context():
            cost = services.calculate_shipping_cost(2.0, DeliverySpeed.STANDARD)
            assert cost == 80.0  # 60 + 2*10

    def test_calculate_shipping_cost_overnight(self, app):
        """測試隔夜達運費計算"""
        with app.app_context():
            cost = services.calculate_shipping_cost(3.0, DeliverySpeed.OVERNIGHT)
            assert cost == 210.0  # 150 + 3*20

    def test_bill_creation_with_package(self, app, sample_customer):
        """測試帳單隨包裹建立"""
        with app.app_context():
            pkg = services.create_package(
                sample_customer,
                {'name': 'R', 'address': 'A', 'phone': 'P'},
                {'weight': 2.0, 'width': 10, 'height': 10, 'length': 10,
                 'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'}
            )
            
            assert pkg.bill is not None
            assert pkg.bill.amount == 80.0  # 60 + 2*10
            assert pkg.bill.customer_id == sample_customer

    def test_credit_card_payment_auto_paid(self, app, sample_customer):
        """測試信用卡付款自動標記為已付"""
        with app.app_context():
            pkg = services.create_package(
                sample_customer,
                {'name': 'R', 'address': 'A', 'phone': 'P'},
                {'weight': 1.0, 'width': 10, 'height': 10, 'length': 10,
                 'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'},
                payment_method=PaymentMethod.CREDIT_CARD
            )
            
            assert pkg.bill.payment_method == PaymentMethod.CREDIT_CARD
            assert pkg.bill.is_paid == True
            assert pkg.bill.paid_at is not None

    def test_mobile_payment_auto_paid(self, app, sample_customer):
        """測試行動支付自動標記為已付"""
        with app.app_context():
            pkg = services.create_package(
                sample_customer,
                {'name': 'R', 'address': 'A', 'phone': 'P'},
                {'weight': 1.0, 'width': 10, 'height': 10, 'length': 10,
                 'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'},
                payment_method=PaymentMethod.MOBILE_PAYMENT
            )
            
            assert pkg.bill.payment_method == PaymentMethod.MOBILE_PAYMENT
            assert pkg.bill.is_paid == True

    def test_cash_payment_unpaid(self, app, sample_customer):
        """測試現金付款未標記為已付"""
        with app.app_context():
            pkg = services.create_package(
                sample_customer,
                {'name': 'R', 'address': 'A', 'phone': 'P'},
                {'weight': 1.0, 'width': 10, 'height': 10, 'length': 10,
                 'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'},
                payment_method=PaymentMethod.CASH
            )
            
            assert pkg.bill.payment_method == PaymentMethod.CASH
            assert pkg.bill.is_paid == False

    def test_prepaid_customer_balance_deduction(self, app):
        """測試預付客戶餘額扣除"""
        with app.app_context():
            customer = models.Customer(
                username="prepaid_test",
                full_name="預付測試",
                email="prepaid_test@test.com",
                phone="0912345678",
                role=UserRole.CUSTOMER,
                customer_type=CustomerType.PREPAID,
                balance=500.0
            )
            customer.set_password("test123")
            db.session.add(customer)
            db.session.commit()
            
            pkg = services.create_package(
                customer.id,
                {'name': 'R', 'address': 'A', 'phone': 'P'},
                {'weight': 2.0, 'width': 10, 'height': 10, 'length': 10,
                 'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'}
            )
            
            db.session.refresh(customer)
            assert customer.balance == 420.0  # 500 - 80
            assert pkg.bill.is_paid == True
            assert pkg.bill.payment_method == PaymentMethod.PREPAID

    def test_pay_bill_with_balance_success(self, app, sample_customer):
        """測試使用餘額支付帳單 - 成功"""
        with app.app_context():
            customer = db.session.get(models.Customer, sample_customer)
            customer.balance = 200.0
            db.session.commit()
            
            pkg = services.create_package(
                sample_customer,
                {'name': 'R', 'address': 'A', 'phone': 'P'},
                {'weight': 1.0, 'width': 10, 'height': 10, 'length': 10,
                 'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'},
                payment_method=PaymentMethod.CASH  # 現金代表延後付款
            )
            
            success, msg = services.pay_bill_with_balance(pkg.bill.id, sample_customer)
            assert success == True
            
            db.session.refresh(customer)
            assert customer.balance == 130.0  # 200 - 70
            assert pkg.bill.is_paid == True

    def test_pay_bill_with_balance_insufficient(self, app, sample_customer):
        """測試使用餘額支付帳單 - 餘額不足"""
        with app.app_context():
            customer = db.session.get(models.Customer, sample_customer)
            customer.balance = 50.0  # 不足
            db.session.commit()
            
            pkg = services.create_package(
                sample_customer,
                {'name': 'R', 'address': 'A', 'phone': 'P'},
                {'weight': 1.0, 'width': 10, 'height': 10, 'length': 10,
                 'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'},
                payment_method=PaymentMethod.CASH
            )
            
            success, msg = services.pay_bill_with_balance(pkg.bill.id, sample_customer)
            assert success == False
            assert "Insufficient" in msg

    def test_top_up_balance(self, app, sample_customer):
        """測試儲值功能"""
        with app.app_context():
            customer = db.session.get(models.Customer, sample_customer)
            initial_balance = customer.balance or 0
            
            services.top_up_balance(sample_customer, 500.0)
            
            db.session.refresh(customer)
            assert customer.balance == initial_balance + 500.0

    def test_get_customer_bills(self, app, sample_customer):
        """測試取得客戶帳單列表"""
        with app.app_context():
            # 建立多個包裹
            for _ in range(3):
                services.create_package(
                    sample_customer,
                    {'name': 'R', 'address': 'A', 'phone': 'P'},
                    {'weight': 1.0, 'width': 10, 'height': 10, 'length': 10,
                     'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'}
                )
            
            bills = services.get_customer_bills(sample_customer)
            assert len(bills) == 3


# ===== 5. 倉儲功能測試 (Warehouse Tests) =====

class TestWarehouseOperations:
    """測試倉儲操作相關功能"""

    def test_warehouse_record_tracking_event(self, app, sample_customer, sample_warehouse_staff):
        """測試倉儲人員記錄追蹤事件"""
        with app.app_context():
            pkg = services.create_package(
                sample_customer,
                {'name': 'R', 'address': 'A', 'phone': 'P'},
                {'weight': 1.0, 'width': 10, 'height': 10, 'length': 10,
                 'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'}
            )
            
            wh_staff = db.session.get(models.WarehouseStaff, sample_warehouse_staff)
            wh_staff.record_tracking_event(pkg.tracking_number, "SORTING", "分揀完成")
            
            updated_pkg = services.get_package_by_tracking(pkg.tracking_number)
            assert updated_pkg.status == PackageStatus.SORTING
            assert updated_pkg.tracking_events[-1].location == "WH-TAIPEI-001"

    def test_warehouse_handle_anomaly(self, app, sample_customer, sample_warehouse_staff):
        """測試倉儲人員處理包裹異常"""
        with app.app_context():
            pkg = services.create_package(
                sample_customer,
                {'name': 'R', 'address': 'A', 'phone': 'P'},
                {'weight': 1.0, 'width': 10, 'height': 10, 'length': 10,
                 'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'}
            )
            
            wh_staff = db.session.get(models.WarehouseStaff, sample_warehouse_staff)
            wh_staff.handle_package_anomaly(pkg.tracking_number, "外箱嚴重損壞")
            
            updated_pkg = services.get_package_by_tracking(pkg.tracking_number)
            assert updated_pkg.status == PackageStatus.DAMAGED
            assert "外箱嚴重損壞" in updated_pkg.tracking_events[-1].description

    def test_update_package_details(self, app, sample_customer):
        """測試更新包裹詳細資訊"""
        with app.app_context():
            pkg = services.create_package(
                sample_customer,
                {'name': 'R', 'address': 'A', 'phone': 'P'},
                {'weight': 1.0, 'width': 10, 'height': 10, 'length': 10,
                 'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'}
            )
            
            original_cost = pkg.shipping_cost
            
            # 更新重量
            services.update_package_details(pkg.tracking_number, {'weight': 5.0})
            
            updated_pkg = services.get_package_by_tracking(pkg.tracking_number)
            assert updated_pkg.weight == 5.0
            assert updated_pkg.shipping_cost > original_cost  # 運費應該增加

    def test_update_package_details_dimensions(self, app, sample_customer):
        """測試更新包裹尺寸"""
        with app.app_context():
            pkg = services.create_package(
                sample_customer,
                {'name': 'R', 'address': 'A', 'phone': 'P'},
                {'weight': 1.0, 'width': 10, 'height': 10, 'length': 10,
                 'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'}
            )
            
            services.update_package_details(pkg.tracking_number, {
                'width': 20, 'height': 25, 'length': 30
            })
            
            updated_pkg = services.get_package_by_tracking(pkg.tracking_number)
            assert updated_pkg.width == 20
            assert updated_pkg.height == 25
            assert updated_pkg.length == 30

    def test_update_package_flags(self, app, sample_customer):
        """測試更新包裹標記"""
        with app.app_context():
            pkg = services.create_package(
                sample_customer,
                {'name': 'R', 'address': 'A', 'phone': 'P'},
                {'weight': 1.0, 'width': 10, 'height': 10, 'length': 10,
                 'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'}
            )
            
            services.update_package_details(pkg.tracking_number, {
                'is_fragile': True, 'is_hazardous': True
            })
            
            updated_pkg = services.get_package_by_tracking(pkg.tracking_number)
            assert updated_pkg.is_fragile == True
            assert updated_pkg.is_hazardous == True


# ===== 6. 司機派送測試 (Driver Delivery Tests) =====

class TestDriverOperations:
    """測試司機派送相關功能"""

    def test_auto_assign_packages(self, app, sample_customer, sample_driver):
        """測試自動分配包裹給司機"""
        with app.app_context():
            # 建立多個待分揀包裹
            for i in range(3):
                pkg = services.create_package(
                    sample_customer,
                    {'name': f'R{i}', 'address': f'A{i}', 'phone': f'P{i}'},
                    {'weight': 1.0, 'width': 10, 'height': 10, 'length': 10,
                     'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'}
                )
                # 設為分揀狀態
                services.add_tracking_event(pkg.tracking_number, "SORTING", "Hub", "Sorted")
            
            # 自動分配
            count = services.auto_assign_packages()
            assert count == 3
            
            # 驗證分配結果
            packages = services.get_user_packages(sample_customer)
            for pkg in packages:
                assert pkg.assigned_driver_id is not None
                assert pkg.status == PackageStatus.OUT_FOR_DELIVERY

    def test_get_packages_for_driver(self, app, sample_customer, sample_driver):
        """測試取得司機派送清單"""
        with app.app_context():
            # 建立包裹並分配給司機
            pkg = services.create_package(
                sample_customer,
                {'name': 'R', 'address': 'A', 'phone': 'P'},
                {'weight': 1.0, 'width': 10, 'height': 10, 'length': 10,
                 'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'}
            )
            
            # 設為分揀狀態並指定司機
            pkg.status = PackageStatus.SORTING
            pkg.assigned_driver_id = sample_driver
            db.session.commit()
            
            packages = services.get_packages_for_driver(sample_driver)
            assert len(packages) >= 1

    def test_driver_complete_delivery(self, app, sample_customer, sample_driver):
        """測試司機完成配送"""
        with app.app_context():
            pkg = services.create_package(
                sample_customer,
                {'name': 'R', 'address': 'A', 'phone': 'P'},
                {'weight': 1.0, 'width': 10, 'height': 10, 'length': 10,
                 'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'}
            )
            
            # 模擬配送流程
            services.add_tracking_event(pkg.tracking_number, "OUT_FOR_DELIVERY", "配送車", "開始配送", sample_driver)
            services.add_tracking_event(pkg.tracking_number, "DELIVERED", "收件地址", "已送達簽收", sample_driver)
            
            updated_pkg = services.get_package_by_tracking(pkg.tracking_number)
            assert updated_pkg.status == PackageStatus.DELIVERED

    def test_driver_report_delay(self, app, sample_customer, sample_driver):
        """測試司機回報延遲"""
        with app.app_context():
            pkg = services.create_package(
                sample_customer,
                {'name': 'R', 'address': 'A', 'phone': 'P'},
                {'weight': 1.0, 'width': 10, 'height': 10, 'length': 10,
                 'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'}
            )
            
            services.add_tracking_event(pkg.tracking_number, "DELAYED", "配送途中", "交通壅塞", sample_driver)
            
            updated_pkg = services.get_package_by_tracking(pkg.tracking_number)
            assert updated_pkg.status == PackageStatus.DELAYED
            assert updated_pkg.status_label == "配送延誤"


# ===== 7. 搜尋功能測試 (Search Tests) =====

class TestSearchFunctions:
    """測試搜尋功能"""

    def test_search_users_by_username(self, app):
        """測試依使用者名稱搜尋"""
        with app.app_context():
            users = [
                models.Customer(username="john_doe", full_name="John Doe", email="john@test.com", phone="1", role=UserRole.CUSTOMER),
                models.Customer(username="jane_doe", full_name="Jane Doe", email="jane@test.com", phone="2", role=UserRole.CUSTOMER),
                models.Customer(username="bob_smith", full_name="Bob Smith", email="bob@test.com", phone="3", role=UserRole.CUSTOMER),
            ]
            for u in users:
                u.set_password("123")
            db.session.add_all(users)
            db.session.commit()
            
            results = services.search_users("doe")
            assert len(results) == 2

    def test_search_users_by_email(self, app):
        """測試依電子郵件搜尋"""
        with app.app_context():
            user = models.Customer(username="test_user", full_name="Test", email="unique.email@test.com", phone="123", role=UserRole.CUSTOMER)
            user.set_password("123")
            db.session.add(user)
            db.session.commit()
            
            results = services.search_users("unique.email")
            assert len(results) == 1
            assert results[0].email == "unique.email@test.com"

    def test_search_users_by_phone(self, app):
        """測試依電話號碼搜尋"""
        with app.app_context():
            user = models.Customer(username="phone_user", full_name="Phone User", email="phone@test.com", phone="0987654321", role=UserRole.CUSTOMER)
            user.set_password("123")
            db.session.add(user)
            db.session.commit()
            
            results = services.search_users("0987654321")
            assert len(results) == 1

    def test_search_packages_by_tracking(self, app, sample_customer):
        """測試依追蹤號碼搜尋包裹"""
        with app.app_context():
            pkg = services.create_package(
                sample_customer,
                {'name': 'R', 'address': 'A', 'phone': 'P'},
                {'weight': 1.0, 'width': 10, 'height': 10, 'length': 10,
                 'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'}
            )
            
            # 使用部分追蹤號碼搜尋
            partial_tn = pkg.tracking_number[3:8]  # 取部分字串
            results = services.search_packages(tracking_number=partial_tn)
            assert len(results) >= 1
            assert pkg in results

    def test_search_packages_by_customer(self, app, sample_customer):
        """測試依客戶帳號搜尋包裹"""
        with app.app_context():
            services.create_package(
                sample_customer,
                {'name': 'R', 'address': 'A', 'phone': 'P'},
                {'weight': 1.0, 'width': 10, 'height': 10, 'length': 10,
                 'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'}
            )
            
            results = services.search_packages(customer_username="sample_customer")
            assert len(results) >= 1

    def test_search_packages_by_date_range(self, app, sample_customer):
        """測試依日期範圍搜尋包裹"""
        with app.app_context():
            pkg = services.create_package(
                sample_customer,
                {'name': 'R', 'address': 'A', 'phone': 'P'},
                {'weight': 1.0, 'width': 10, 'height': 10, 'length': 10,
                 'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'}
            )
            
            # 搜尋今天建立的包裹
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow = today + timedelta(days=1)
            
            results = services.search_packages(date_from=today, date_to=tomorrow)
            assert len(results) >= 1
            assert pkg in results

    def test_get_packages_by_status(self, app, sample_customer):
        """測試依狀態篩選包裹"""
        with app.app_context():
            pkg1 = services.create_package(
                sample_customer,
                {'name': 'R1', 'address': 'A1', 'phone': 'P1'},
                {'weight': 1.0, 'width': 10, 'height': 10, 'length': 10,
                 'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'}
            )
            
            pkg2 = services.create_package(
                sample_customer,
                {'name': 'R2', 'address': 'A2', 'phone': 'P2'},
                {'weight': 1.0, 'width': 10, 'height': 10, 'length': 10,
                 'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'}
            )
            
            # 更新 pkg1 狀態
            services.add_tracking_event(pkg1.tracking_number, "SORTING", "Hub", "Sorted")
            
            results = services.get_packages_by_status([PackageStatus.CREATED])
            assert pkg2 in results
            
            results2 = services.get_packages_by_status([PackageStatus.SORTING])
            assert pkg1 in results2


# ===== 8. 定價規則測試 (Pricing Rules Tests) =====

class TestPricingRules:
    """測試定價規則相關功能"""

    def test_get_all_pricing_rules(self, app):
        """測試取得所有定價規則"""
        with app.app_context():
            rules = services.get_all_pricing_rules()
            assert len(rules) == 4  # 預設建立了 4 種速度的規則

    def test_update_pricing_rule(self, app):
        """測試更新定價規則"""
        with app.app_context():
            rules = services.get_all_pricing_rules()
            rule = rules[0]
            original_base = rule.base_rate
            
            services.update_pricing_rule(rule.id, 200.0, 30.0)
            
            db.session.expire_all()
            updated_rule = db.session.get(models.PricingRule, rule.id)
            assert updated_rule.base_rate == 200.0
            assert updated_rule.rate_per_kg == 30.0

    def test_pricing_rule_affects_new_packages(self, app, sample_customer):
        """測試定價規則變更影響新包裹"""
        with app.app_context():
            # 取得標準速遞規則並更新
            rules = services.get_all_pricing_rules()
            standard_rule = next(r for r in rules if r.service_type == DeliverySpeed.STANDARD)
            services.update_pricing_rule(standard_rule.id, 100.0, 20.0)
            
            db.session.expire_all()
            
            # 建立新包裹
            pkg = services.create_package(
                sample_customer,
                {'name': 'R', 'address': 'A', 'phone': 'P'},
                {'weight': 2.0, 'width': 10, 'height': 10, 'length': 10,
                 'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'}
            )
            
            # 運費應為新規則計算: 100 + 2*20 = 140
            assert pkg.shipping_cost == 140.0


# ===== 9. 系統日誌測試 (Audit Log Tests) =====

class TestAuditLog:
    """測試系統日誌功能"""

    def test_log_audit(self, app, sample_customer):
        """測試記錄審計日誌"""
        with app.app_context():
            log = services.log_audit(
                sample_customer,
                "TEST_ACTION",
                target_id="TW-12345678",
                details="測試日誌記錄"
            )
            
            assert log is not None
            assert log.action == "TEST_ACTION"
            assert log.target_id == "TW-12345678"
            assert log.details == "測試日誌記錄"

    def test_log_audit_timestamp(self, app, sample_customer):
        """測試審計日誌時間戳"""
        with app.app_context():
            before = datetime.now()
            log = services.log_audit(sample_customer, "TIMESTAMP_TEST")
            after = datetime.now()
            
            assert log.timestamp >= before
            assert log.timestamp <= after


# ===== 10. 整合測試 (Integration Tests) =====

class TestIntegration:
    """整合測試 - 測試完整的業務流程"""

    def test_complete_delivery_flow(self, app, sample_customer, sample_driver, sample_warehouse_staff):
        """測試完整的寄送流程"""
        with app.app_context():
            # 1. 客戶建立包裹
            pkg = services.create_package(
                sample_customer,
                {'name': '王小明', 'address': '台北市信義區信義路五段7號', 'phone': '0912345678'},
                {'weight': 2.5, 'width': 20, 'height': 15, 'length': 30,
                 'package_type': 'MEDIUM_BOX', 'delivery_speed': 'STANDARD'},
                payment_method=PaymentMethod.CREDIT_CARD
            )
            
            assert pkg.status == PackageStatus.CREATED
            assert pkg.bill.is_paid == True
            
            # 2. 司機取件
            services.add_tracking_event(pkg.tracking_number, "PICKED_UP", "客戶地址", "已取件", sample_driver)
            
            # 3. 送達倉庫
            services.add_tracking_event(pkg.tracking_number, "IN_TRANSIT", "幹線運輸", "運送中")
            
            # 4. 倉儲處理
            wh_staff = db.session.get(models.WarehouseStaff, sample_warehouse_staff)
            wh_staff.record_tracking_event(pkg.tracking_number, "SORTING", "分揀完成")
            
            # 5. 自動分配司機
            pkg_obj = services.get_package_by_tracking(pkg.tracking_number)
            pkg_obj.status = PackageStatus.SORTING
            pkg_obj.assigned_driver_id = None
            db.session.commit()
            
            count = services.auto_assign_packages()
            assert count >= 1
            
            # 6. 派送中
            pkg_refresh = services.get_package_by_tracking(pkg.tracking_number)
            assert pkg_refresh.status == PackageStatus.OUT_FOR_DELIVERY
            
            # 7. 完成配送
            services.add_tracking_event(pkg.tracking_number, "DELIVERED", "收件地址", "已簽收")
            
            final_pkg = services.get_package_by_tracking(pkg.tracking_number)
            assert final_pkg.status == PackageStatus.DELIVERED
            assert len(final_pkg.tracking_events) >= 5

    def test_exception_handling_flow(self, app, sample_customer, sample_warehouse_staff):
        """測試異常處理流程"""
        with app.app_context():
            # 建立包裹
            pkg = services.create_package(
                sample_customer,
                {'name': 'R', 'address': 'A', 'phone': 'P'},
                {'weight': 1.0, 'width': 10, 'height': 10, 'length': 10,
                 'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'},
                payment_method=PaymentMethod.CASH
            )
            
            # 倉儲發現損壞
            wh_staff = db.session.get(models.WarehouseStaff, sample_warehouse_staff)
            wh_staff.handle_package_anomaly(pkg.tracking_number, "包裹外箱破損，內容物受損")
            
            damaged_pkg = services.get_package_by_tracking(pkg.tracking_number)
            assert damaged_pkg.status == PackageStatus.DAMAGED
            
            # 帳單應未付款（現金）
            assert damaged_pkg.bill.is_paid == False

    def test_multiple_customers_multiple_packages(self, app):
        """測試多客戶多包裹情境"""
        with app.app_context():
            # 建立多個客戶
            customers = []
            for i in range(3):
                c = models.Customer(
                    username=f"customer{i}",
                    full_name=f"客戶{i}",
                    email=f"c{i}@test.com",
                    phone=f"091234567{i}",
                    role=UserRole.CUSTOMER
                )
                c.set_password("123")
                customers.append(c)
            db.session.add_all(customers)
            db.session.commit()
            
            # 每個客戶建立多個包裹
            for c in customers:
                for j in range(2):
                    services.create_package(
                        c.id,
                        {'name': f'R{j}', 'address': f'A{j}', 'phone': f'P{j}'},
                        {'weight': 1.0, 'width': 10, 'height': 10, 'length': 10,
                         'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'}
                    )
            
            # 驗證每個客戶的包裹數量
            for c in customers:
                packages = services.get_user_packages(c.id)
                assert len(packages) == 2
