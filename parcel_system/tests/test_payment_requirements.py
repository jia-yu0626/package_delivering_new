
import pytest
from app import create_app, db, models, services

@pytest.fixture
def app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False  # Disable CSRF for easier form posting
    })
    
    with app.app_context():
        db.create_all()
        # Setup Pricing Rules - REQUIRED for package creation
        rules = [models.PricingRule(service_type=models.DeliverySpeed.STANDARD, base_rate=100.0, rate_per_kg=10.0)]
        db.session.add_all(rules)
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_client(client, app):
    # Helper to login
    def login(user):
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
            sess['user_name'] = user.full_name
            sess['user_role'] = user.role.value
            # Also set customer_type for the route logic
            if hasattr(user, 'customer_type'):
                sess['customer_type'] = user.customer_type.value
    return login

def create_customer(username, c_type, balance=0.0):
    user = models.Customer(
        username=username,
        full_name=username,
        email=f"{username}@test.com",
        phone="123",
        role=models.UserRole.CUSTOMER,
        customer_type=c_type,
        balance=balance
    )
    user.set_password('password')
    db.session.add(user)
    db.session.commit()
    return user

def get_package_data():
    return {
        'recipient_name': 'Test Recipient',
        'recipient_address': 'Test Address',
        'recipient_phone': '0912345678',
        'weight': '1.0',
        'width': '10',
        'height': '10',
        'length': '10',
        'package_type': 'SMALL_BOX',
        'delivery_speed': 'STANDARD'
        # 'payment_method' will be added per test
    }

def test_contract_customer_payment(app, client, auth_client):
    """1. 合約客戶，顯示其餘額帳號 (Billing to Monthly)"""
    with app.app_context():
        user = create_customer('contract_user', models.CustomerType.CONTRACT)
        auth_client(user)
        
        # Test using services directly instead of HTTP (more reliable for unit tests)
        pkg = services.create_package(
            user.id,
            {'name': 'Test Recipient', 'address': 'Test Address', 'phone': '0912345678'},
            {'weight': 1.0, 'width': 10, 'height': 10, 'length': 10, 'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'},
            payment_method=models.PaymentMethod.MONTHLY
        )
        
        # Verify Bill
        assert pkg.bill.payment_method == models.PaymentMethod.MONTHLY
        assert pkg.bill.is_paid == False  # Monthly bills are paid later

def test_non_contract_customer_payment(app, client, auth_client):
    """2. 非合約客戶，可選擇用信用卡，現金，行動支付付款"""
    with app.app_context():
        user = create_customer('normal_user', models.CustomerType.NON_CONTRACT)
        auth_client(user)
        
        # Test CASH
        pkg1 = services.create_package(
            user.id,
            {'name': 'R', 'address': 'A', 'phone': 'P'},
            {'weight': 1.0, 'width': 10, 'height': 10, 'length': 10, 'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'},
            payment_method=models.PaymentMethod.CASH
        )
        assert pkg1.bill.payment_method == models.PaymentMethod.CASH
        assert pkg1.bill.is_paid == False
        
        # Test CREDIT_CARD
        pkg2 = services.create_package(
            user.id,
            {'name': 'R', 'address': 'A', 'phone': 'P'},
            {'weight': 1.0, 'width': 10, 'height': 10, 'length': 10, 'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'},
            payment_method=models.PaymentMethod.CREDIT_CARD
        )
        assert pkg2.bill.payment_method == models.PaymentMethod.CREDIT_CARD
        assert pkg2.bill.is_paid == True  # Instant payment
        
        # Test MOBILE_PAYMENT
        pkg3 = services.create_package(
            user.id,
            {'name': 'R', 'address': 'A', 'phone': 'P'},
            {'weight': 1.0, 'width': 10, 'height': 10, 'length': 10, 'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'},
            payment_method=models.PaymentMethod.MOBILE_PAYMENT
        )
        assert pkg3.bill.payment_method == models.PaymentMethod.MOBILE_PAYMENT
        assert pkg3.bill.is_paid == True

def test_prepaid_customer_payment(app, client, auth_client):
    """3. 預付客戶，餘額自動扣除"""
    with app.app_context():
        user = create_customer('prepaid_user', models.CustomerType.PREPAID, balance=1000.0)
        auth_client(user)
        
        initial_balance = user.balance
        
        # Create package - prepaid customers automatically use PREPAID payment method
        pkg = services.create_package(
            user.id,
            {'name': 'R', 'address': 'A', 'phone': 'P'},
            {'weight': 1.0, 'width': 10, 'height': 10, 'length': 10, 'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'}
        )
        
        # Verify package created and balance deducted
        db.session.refresh(user)
        assert user.balance < initial_balance
        assert pkg.bill.payment_method == models.PaymentMethod.PREPAID
        assert pkg.bill.is_paid == True  # Prepaid is auto-paid
