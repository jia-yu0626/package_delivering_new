
from app import create_app, db, models, services
from app.models import UserRole, PackageStatus, DeliverySpeed, PackageType

def assign_packages():
    app = create_app()
    with app.app_context():
        # 1. Get the driver
        driver = db.session.execute(db.select(models.User).filter_by(username='driver')).scalar_one_or_none()
        if not driver:
            print("Driver 'driver' not found. Please run reinit_users.py first.")
            return

        print(f"Found driver: {driver.full_name} (ID: {driver.id})")

        # 2. Get the customer (sender)
        customer = db.session.execute(db.select(models.User).filter_by(username='customer')).scalar_one_or_none()
        if not customer:
            print("Customer 'customer' not found. Creating dummy customer...")
            customer = models.Customer(username="temp_customer", full_name="Temp Customer", email="temp@c.com", phone="000", role=UserRole.CUSTOMER)
            customer.set_password("123")
            db.session.add(customer)
            db.session.commit()

        # 3. Check for existing packages or create some
        packages = db.session.execute(db.select(models.Package)).scalars().all()
        
        if not packages:
            print("No packages found in DB. Creating 3 test packages...")
            for i in range(1, 4):
                pkg = models.Package(
                    tracking_number=services.generate_tracking_number(),
                    sender_id=customer.id,
                    recipient_name=f"Recipient {i}",
                    recipient_address=f"Address {i}",
                    recipient_phone="0900000000",
                    weight=2.0 + i,
                    width=10, height=10, length=10,
                    package_type=PackageType.SMALL_BOX,
                    delivery_speed=DeliverySpeed.STANDARD,
                    status=PackageStatus.SORTING # Start as SORTING so they are eligible for assignment logic generally
                )
                db.session.add(pkg)
            db.session.commit()
            packages = db.session.execute(db.select(models.Package)).scalars().all()

        # 4. Assign packages to driver
        count = 0
        for pkg in packages:
            # Assign if not already assigned (or just force assign for this demo)
            pkg.assigned_driver_id = driver.id
            # Also update status to OUT_FOR_DELIVERY for visual variety if it's not already delivered
            if pkg.status in [PackageStatus.CREATED, PackageStatus.PICKED_UP, PackageStatus.SORTING]:
                 pkg.status = PackageStatus.OUT_FOR_DELIVERY
            
            count += 1
            print(f"Assigned package {pkg.tracking_number} to driver {driver.username} (Status: {pkg.status.value})")
        
        db.session.commit()
        print(f"\nSuccessfully assigned {count} packages to driver '{driver.username}'.")
        print("You can now login as 'driver' (password: 123456) to view them on dashboard_employee.html.")

if __name__ == "__main__":
    assign_packages()
