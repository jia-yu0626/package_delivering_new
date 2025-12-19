from app import create_app, db, models
from datetime import datetime

app = create_app()

with app.app_context():
    # Get Normal User
    user = db.session.execute(db.select(models.Customer).filter_by(username='normal')).scalar_one_or_none()
    if user:
        # Create Package
        pkg = models.Package(
            tracking_number='T12345678',
            sender_id=user.id,
            recipient_name='Test Recipient',
            recipient_address='123 Test St',
            recipient_phone='555-0000',
            weight=1.5,
            width=10,
            height=10,
            length=10,
            status=models.PackageStatus.EXCEPTION, # Set to EXCEPTION to test dashboard
            delivery_speed=models.DeliverySpeed.STANDARD
        )
        
        # Check if exists
        curr = db.session.execute(db.select(models.Package).filter_by(tracking_number='T12345678')).scalar_one_or_none()
        if not curr:
            db.session.add(pkg)
            # Create an event
            event = models.TrackingEvent(
                package=pkg,
                status=models.PackageStatus.EXCEPTION,
                location='Test Hub',
                description='Package damaged during sorting'
            )
            db.session.add(event)
            
            # Create a Bill (to test billing view)
            bill = models.Bill(
                customer=user,
                package=pkg,
                amount=150.0
            )
            db.session.add(bill)
            
            db.session.commit()
            print("Created test package 'T12345678' (Exception) and Bill for 'normal' user")
        else:
            print("Test package already exists")
    else:
        print("User 'normal' not found. Run setup_test_users.py first.")
