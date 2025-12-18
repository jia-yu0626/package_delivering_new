
import pytest
from app import create_app, db, models, services
from datetime import datetime

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

def test_customer_prepaid_flow(app):
    """Test Customer creation, package creation, and prepaid balance payment."""
    with app.app_context():
        # 1. Create Prepaid Customer
        customer = models.Customer(
            username='prepaid_user', full_name='Prepaid User', email='prepaid@test.com', phone='123',
            role=models.UserRole.CUSTOMER, balance=500.0
        )
        customer.set_password('123')
        db.session.add(customer)
        db.session.commit()
        
        # 2. Create Package
        pkg = services.create_package(
            customer.id,
            {'name': 'R', 'address': 'A', 'phone': 'P'},
            {'weight': 2.0, 'width': 10, 'height': 10, 'length': 10, 'package_type': 'SMALL_BOX', 'delivery_speed': 'STANDARD'}
        )
        
        # Cost should be 100 + 2*10 = 120
        assert pkg.shipping_cost == 120.0
        assert pkg.bill is not None
        assert pkg.bill.is_paid == False
        
        # 3. Pay with Balance
        success, msg = services.pay_bill_with_balance(pkg.bill.id, customer.id)
        assert success is True
        assert pkg.bill.is_paid is True
        assert customer.balance == 380.0 # 500 - 120

def test_warehouse_flow(app):
    """Test Warehouse attribute updates and sorting."""
    with app.app_context():
        customer = models.Customer(username='c', full_name='C', email='c@t.com', phone='1', role=models.UserRole.CUSTOMER)
        customer.set_password('123')
        wh = models.Employee(username='wh', full_name='WH', email='wh@t.com', phone='2', role=models.UserRole.WAREHOUSE, department='Logistics')
        wh.set_password('123')
        db.session.add_all([customer, wh])
        db.session.commit()
        
        pkg = services.create_package(customer.id, {'name':'R','address':'A','phone':'P'}, 
                                    {'weight':5, 'width':10, 'height':10, 'length':10, 'package_type':'SMALL_BOX', 'delivery_speed':'STANDARD'})
        
        # 1. Update Attributes
        new_data = {'weight': 10.0}
        services.update_package_details(pkg.tracking_number, new_data)
        
        updated_pkg = services.get_package_by_tracking(pkg.tracking_number)
        assert updated_pkg.weight == 10.0
        # Cost recalculation check: 100 + 10*10 = 200 (Old was 100+5*10=150)
        assert updated_pkg.shipping_cost == 200.0
        
        # 2. Sort Package
        services.add_tracking_event(pkg.tracking_number, "SORTING", "Hub", "Sorted", wh.id)
        assert updated_pkg.status == models.PackageStatus.SORTING

def test_driver_flow(app):
    """Test Driver delivery list and exception reporting."""
    with app.app_context():
        customer = models.Customer(username='c', full_name='C', email='c@t.com', phone='1', role=models.UserRole.CUSTOMER)
        customer.set_password('123')
        driver = models.Employee(username='dr', full_name='D', email='d@t.com', phone='2', role=models.UserRole.DRIVER, department='Transport')
        driver.set_password('123')
        db.session.add_all([customer, driver])
        db.session.commit()
        
        pkg = services.create_package(customer.id, {'name':'R','address':'A','phone':'P'}, 
                                    {'weight':1, 'width':1, 'height':1, 'length':1, 'package_type':'SMALL_BOX', 'delivery_speed':'STANDARD'})
        
        # Make package ready for driver (SORTING)
        services.add_tracking_event(pkg.tracking_number, "SORTING", "Hub", "Sorted")
        
        # 1. Check Driver List
        list = services.get_packages_for_driver(driver.id)
        assert pkg in list
        
        # 2. Driver pickup
        services.add_tracking_event(pkg.tracking_number, "OUT_FOR_DELIVERY", "Truck", "Go", driver.id)
        assert pkg.status == models.PackageStatus.OUT_FOR_DELIVERY
        
        # 3. Exception
        services.add_tracking_event(pkg.tracking_number, "DELAYED", "Road", "Traffic", driver.id)
        assert pkg.status == models.PackageStatus.DELAYED

def test_cs_admin_flow(app):
    """Test CS search and Admin pricing update."""
    with app.app_context():
        customer = models.Customer(username='target', full_name='Target User', email='t@t.com', phone='1', role=models.UserRole.CUSTOMER)
        customer.set_password('123')
        db.session.add(customer)
        db.session.commit()
        
        # 1. CS Search
        results = services.search_users("Target")
        assert len(results) == 1
        assert results[0].username == 'target'
        
        # 2. Admin Pricing
        rule = services.get_all_pricing_rules()[0]
        services.update_pricing_rule(rule.id, 500.0, 50.0)
        
        db.session.expire_all()
        updated_rule = db.session.get(models.PricingRule, rule.id)
        assert updated_rule.base_rate == 500.0
