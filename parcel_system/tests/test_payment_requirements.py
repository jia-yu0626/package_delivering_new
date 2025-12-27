
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
        
        # Determine expected behavior:
        # Contract user logic in routes.py automatically sets PaymentMethod.MONTHLY
        
        data = get_package_data()
        # No payment_method sent in form for Contract user usually, or ignored
        
        resp = client.post('/create_package', data=data, follow_redirects=True)
        assert resp.status_code == 200
        assert b"Success" in resp.data or "建立成功".encode('utf-8') in resp.data
        
        # Verify Bill
        pkg = db.session.execute(db.select(models.Package).filter_by(sender_id=user.id)).scalar_one()
        bill = db.session.execute(db.select(models.Bill).filter_by(package_id=pkg.id)).scalar_one()
        
        assert bill.payment_method == models.PaymentMethod.MONTHLY
        assert bill.is_paid == False # Monthly bills are paid later

def test_non_contract_customer_payment(app, client, auth_client):
    """2. 非合約客戶，可選擇用信用卡，現金，行動支付付款"""
    with app.app_context():
        user = create_customer('normal_user', models.CustomerType.NON_CONTRACT)
        auth_client(user)
        
        # Test CASH
        data = get_package_data()
        data['payment_method'] = 'CASH'
        resp = client.post('/create_package', data=data, follow_redirects=True)
        assert resp.status_code == 200
        
        pkg = db.session.execute(db.select(models.Package).order_by(models.Package.id.desc())).scalars().first()
        bill = pkg.bill
        assert bill.payment_method == models.PaymentMethod.CASH
        assert bill.is_paid == False
        
        # Test CREDIT_CARD
        data['payment_method'] = 'CREDIT_CARD'
        resp = client.post('/create_package', data=data, follow_redirects=True)
        pkg = db.session.execute(db.select(models.Package).order_by(models.Package.id.desc())).scalars().first()
        assert pkg.bill.payment_method == models.PaymentMethod.CREDIT_CARD
        assert pkg.bill.is_paid == True # Instant payment
        
        # Test MOBILE_PAYMENT
        data['payment_method'] = 'MOBILE_PAYMENT'
        resp = client.post('/create_package', data=data, follow_redirects=True)
        pkg = db.session.execute(db.select(models.Package).order_by(models.Package.id.desc())).scalars().first()
        assert pkg.bill.payment_method == models.PaymentMethod.MOBILE_PAYMENT
        assert pkg.bill.is_paid == True

def test_prepaid_customer_payment(app, client, auth_client):
    """3. 預付客戶，需提供第三方付款帳號"""
    with app.app_context():
        user = create_customer('prepaid_user', models.CustomerType.PREPAID, balance=1000.0)
        auth_client(user)
        
        # Case A: Missing Third Party Account -> Should Fail
        data = get_package_data()
        # third_party_account missing
        
        resp = client.post('/create_package', data=data, follow_redirects=True)
        # Should stay on page or flash error
        assert b"third_party_account" in resp.data or "提供第三方付款帳號".encode('utf-8') in resp.data # The error message
        
        # Verify no package created
        pkgs = services.get_user_packages(user.id)
        assert len(pkgs) == 0
        
        # Case B: Provided Account -> Success
        data['third_party_account'] = '123-456-789'
        resp = client.post('/create_package', data=data, follow_redirects=True)
        assert resp.status_code == 200
        
        # Verify package created and balance deducted
        user_refreshed = db.session.get(models.Customer, user.id)
        assert user_refreshed.balance < 1000.0
        
        pkgs = services.get_user_packages(user.id)
        assert len(pkgs) == 1
        assert pkgs[0].bill.payment_method == models.PaymentMethod.PREPAID
