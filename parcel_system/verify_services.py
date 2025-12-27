
from app import create_app, db, models, services
from datetime import datetime

def verify_services():
    app = create_app()
    with app.app_context():
        # Setup Test Data
        print("Setting up test data...")
        # Clean up
        db.drop_all()
        db.create_all()
        
        # 1. Create Customer
        customer = models.Customer(
            username="test_svc_user",
            full_name="Test Service User",
            email="test_svc@example.com",
            phone="0911111111",
            address="123 Test St",
            role=models.UserRole.CUSTOMER,
            customer_type=models.CustomerType.NON_CONTRACT
        )
        customer.set_password("password")
        db.session.add(customer)
        db.session.commit()
        
        # 2. Create Pricing Rule
        rule = models.PricingRule(
            service_type=models.DeliverySpeed.STANDARD,
            base_rate=100.0,
            rate_per_kg=10.0
        )
        db.session.add(rule)
        db.session.commit()
        
        print("Test data setup complete.")
        
        # Test create_package
        print("Testing create_package...")
        recipient_data = {
            'name': 'Recipient Name',
            'address': '456 Recipient Rd',
            'phone': '0922222222'
        }
        package_data = {
            'weight': 5.0,
            'width': 10, 'height': 10, 'length': 10,
            'package_type': 'SMALL_BOX',
            'delivery_speed': 'STANDARD',
            'declared_value': 1000
        }
        
        try:
            pkg = services.create_package(
                sender_id=customer.id,
                recipient_data=recipient_data,
                package_data=package_data
            )
            print(f"Package created: {pkg.tracking_number}, Cost: {pkg.shipping_cost}")
            
            # Expected cost: 100 + (5 * 10) = 150
            assert pkg.shipping_cost == 150.0
            assert pkg.status == models.PackageStatus.CREATED
            assert pkg.tracking_number.startswith("TW-")
        except Exception as e:
            print(f"create_package failed: {e}")
            raise

        # Test add_tracking_event
        print("Testing add_tracking_event...")
        services.add_tracking_event(pkg.tracking_number, 'PICKED_UP', 'Warehouse A', 'Picked up by courier')
        
        updated_pkg = services.get_package_by_tracking(pkg.tracking_number)
        assert updated_pkg.status == models.PackageStatus.PICKED_UP
        assert len(updated_pkg.tracking_events) == 2 # Created + Picked Up
        print(f"Tracking event added. Current status: {updated_pkg.status.value}")

        print("Services verification passed!")

if __name__ == "__main__":
    verify_services()
