
import pytest
from app import create_app, db, models, services
from app.models import CustomerType, PaymentMethod, UserRole, PackageStatus

@pytest.fixture
def app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"
    })
    
    with app.app_context():
        db.create_all()
        # Setup Pricing Rules
        rules = [models.PricingRule(service_type=models.DeliverySpeed.STANDARD, base_rate=100.0, rate_per_kg=10.0)]
        db.session.add_all(rules)
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_general_customer_flow(app):
    """Test General Customer creation and Pay-per-use flow"""
    with app.app_context():
        # Setup General Customer
        customer = models.Customer(
            username='gen_user', full_name='General User', email='gen@test.com', phone='111',
            role=UserRole.CUSTOMER, customer_type=CustomerType.NON_CONTRACT
        )
        customer.set_password('123')
        db.session.add(customer)
        db.session.commit()

        # Create Package
        pkg = services.create_package(
            customer.id,
            {'name': 'R', 'address': 'A', 'phone': 'P'},
            {'weight': 2.0, 'width': 10, 'height': 10, 'length': 10, 'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'},
            payment_method=PaymentMethod.CREDIT_CARD
        )
        
        assert pkg.shipping_cost == 120.0 # 100 + 2*10
        assert pkg.bill.amount == 120.0
        assert pkg.bill.is_paid == False
        
        # General customer pays immediately (simulated)
        # Assuming there is a service to mark bill as paid
        pkg.bill.is_paid = True
        pkg.bill.paid_at = models.datetime.now()
        db.session.commit()
        
        assert pkg.bill.is_paid == True
        assert pkg.bill.payment_method == PaymentMethod.CREDIT_CARD

def test_contract_customer_flow(app):
    """Test Contract Customer creation and Monthly Billing flow"""
    with app.app_context():
        # Setup Contract Customer
        customer = models.Customer(
            username='contract_user', full_name='Contract User', email='con@test.com', phone='222',
            role=UserRole.CUSTOMER, customer_type=CustomerType.CONTRACT
        )
        customer.set_password('123')
        db.session.add(customer)
        db.session.commit()

        # Create Package - Should default to MONTHLY payment
        pkg = services.create_package(
            customer.id,
            {'name': 'R', 'address': 'A', 'phone': 'P'},
            {'weight': 5.0, 'width': 10, 'height': 10, 'length': 10, 'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'}
        )
        
        assert pkg.shipping_cost == 150.0 # 100 + 5*10
        assert pkg.bill.amount == 150.0
        assert pkg.bill.payment_method == PaymentMethod.MONTHLY
        assert pkg.bill.is_paid == False
        
        # Verify no immediate payment is required for flow to proceed, 
        # but bill exists for end-of-month aggregation.
        
def test_cs_staff_flow(app):
    """Test CS Staff searching for users and viewing package history"""
    with app.app_context():
        # Setup Data
        c1 = models.Customer(username='u1', full_name='User One', email='u1@t.com', phone='1', role=UserRole.CUSTOMER)
        c2 = models.Customer(username='u2', full_name='User Two', email='u2@t.com', phone='2', role=UserRole.CUSTOMER)
        cs = models.Employee(username='cs', full_name='CS Staff', email='cs@t.com', phone='3', role=UserRole.CS)
        db.session.add_all([c1, c2, cs])
        db.session.commit()
        
        # CS Search
        results = services.search_users("One")
        assert len(results) == 1
        assert results[0].username == 'u1'
        
        # Create package for history check
        pkg = services.create_package(c1.id, {'name':'R','address':'A','phone':'P'}, 
                                    {'weight':1, 'width':1, 'height':1, 'length':1})
        services.add_tracking_event(pkg.tracking_number, "PICKED_UP", "Loc1", "Picked up")
        
        # Fetch package history (simulated by accessing relationship)
        pkg_fetched = services.get_package_by_tracking(pkg.tracking_number)
        assert len(pkg_fetched.tracking_events) == 1
        assert pkg_fetched.tracking_events[0].status == PackageStatus.PICKED_UP

def test_warehouse_staff_flow(app):
    """Test Warehouse Staff receiving, sorting, and reporting damage"""
    with app.app_context():
        # Setup
        wh = models.WarehouseStaff(username='wh', full_name='WH Staff', email='wh@t.com', phone='1', 
                                 role=UserRole.WAREHOUSE, warehouse_location_id="WH-001")
        wh.set_password('123')
        c = models.Customer(username='c', full_name='C', email='c@t.com', phone='2', role=UserRole.CUSTOMER)
        db.session.add_all([wh, c])
        db.session.commit()
        
        # Create Package
        pkg = services.create_package(c.id, {'name':'R','address':'A','phone':'P'}, 
                                    {'weight':10, 'width':10, 'height':10, 'length':10})
        
        # 1. Warehouse Sorts Package
        # Using the method on WarehouseStaff model if available, otherwise service
        wh.record_tracking_event(pkg.tracking_number, "SORTING", "Sorting matchine 1")
        
        updated_pkg = services.get_package_by_tracking(pkg.tracking_number)
        assert updated_pkg.status == PackageStatus.SORTING
        assert updated_pkg.tracking_events[-1].location == "WH-001"
        
        # 2. Handle Anomaly (Damage)
        wh.handle_package_anomaly(pkg.tracking_number, "Box crushed")
        
        updated_pkg_2 = services.get_package_by_tracking(pkg.tracking_number)
        assert updated_pkg_2.status == PackageStatus.DAMAGED
        assert "Box crushed" in updated_pkg_2.tracking_events[-1].description
