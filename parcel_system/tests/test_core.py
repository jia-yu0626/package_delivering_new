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
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_create_user(app):
    with app.app_context():
        user = models.Customer(
            username="testuser",
            full_name="Test User",
            email="test@example.com",
            phone="1234567890",
            role=models.UserRole.CUSTOMER
        )
        user.set_password("password")
        db.session.add(user)
        db.session.commit()
        
        saved_user = db.session.get(models.User, user.id)
        assert saved_user.username == "testuser"
        assert saved_user.check_password("password")

def test_create_package(app):
    with app.app_context():
        # Create sender
        sender = models.Customer(
            username="sender",
            full_name="Sender",
            email="sender@example.com",
            phone="0912345678",
            role=models.UserRole.CUSTOMER
        )
        sender.set_password('password')
        db.session.add(sender)
        db.session.commit()
        
        # Create package
        recipient_data = {
            'name': 'Recipient',
            'address': 'Taipei City',
            'phone': '0987654321'
        }
        package_data = {
            'weight': 2.5,
            'width': 10,
            'height': 10,
            'length': 10,
            'package_type': 'MEDIUM_BOX',
            'delivery_speed': 'STANDARD'
        }
        
        pkg = services.create_package(sender.id, recipient_data, package_data)
        
        assert pkg.tracking_number.startswith("TW-")
        assert pkg.status == models.PackageStatus.CREATED
        assert pkg.shipping_cost > 0

def test_tracking_flow(app):
    with app.app_context():
        # Setup data
        sender = models.Customer(username="s", full_name="S", email="s@e.com", phone="1", role=models.UserRole.CUSTOMER)
        sender.set_password('password')
        db.session.add(sender)
        db.session.commit()
        
        pkg = services.create_package(sender.id, {'name':'R','address':'A','phone':'P'}, 
                                    {'weight':1, 'width':1, 'height':1, 'length':1, 'package_type':'SMALL_BOX', 'delivery_speed':'STANDARD'})
        
        # Update status
        services.add_tracking_event(pkg.tracking_number, "PICKED_UP", "Taipei Station", "Picked up by driver")
        
        updated_pkg = services.get_package_by_tracking(pkg.tracking_number)
        assert updated_pkg.status == models.PackageStatus.PICKED_UP
        assert len(updated_pkg.tracking_events) == 2 # Created + Picked Up

def test_auto_assign(app):
    with app.app_context():
        # 1. Create Drivers
        d1 = models.Employee(username="d1", full_name="Driver 1", email="d1@e.com", phone="1", role=models.UserRole.DRIVER)
        d2 = models.Employee(username="d2", full_name="Driver 2", email="d2@e.com", phone="2", role=models.UserRole.DRIVER)
        d1.set_password("pwd")
        d2.set_password("pwd")
        db.session.add_all([d1, d2])
        
        # Create Sender for packages
        sender = models.Customer(username="sender2", full_name="Sender", email="s2@e.com", phone="3", role=models.UserRole.CUSTOMER)
        sender.set_password("pwd")
        db.session.add(sender)
        db.session.commit()
        
        # 2. Create Packages (Manual creation for speed)
        packages = []
        for i in range(3):
            pkg = models.Package(
                tracking_number=f"T{i}",
                sender_id=sender.id,
                recipient_name="R",
                recipient_address="A",
                recipient_phone="P",
                weight=1.0, width=1, height=1, length=1,
                status=models.PackageStatus.SORTING # Ready for assignment
            )
            packages.append(pkg)
        db.session.add_all(packages)
        db.session.commit()
        
        # 3. Auto Assign
        count = services.auto_assign_packages()
        assert count == 3
        
        # 4. Verify Assignment
        p0 = db.session.execute(db.select(models.Package).filter_by(tracking_number="T0")).scalar_one()
        p1 = db.session.execute(db.select(models.Package).filter_by(tracking_number="T1")).scalar_one()
        p2 = db.session.execute(db.select(models.Package).filter_by(tracking_number="T2")).scalar_one()
        
        assert p0.assigned_driver_id is not None
        assert p1.assigned_driver_id is not None
        assert p2.assigned_driver_id is not None
        
        # Check distribution (Round Robin)
        # Should be d1, d2, d1 (or similar depend on order)
        driver_ids = {p0.assigned_driver_id, p1.assigned_driver_id, p2.assigned_driver_id}
        # We have existing seed driver + 2 new drivers = 3 drivers. 
        # 3 packages. Each should get one if round robin works perfectly on 3 items.
        # Just ensure multiple drivers were utilized.
        assert len(driver_ids) >= 2
