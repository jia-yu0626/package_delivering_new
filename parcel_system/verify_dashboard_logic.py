from app import create_app, db, models

app = create_app()

with app.app_context():
    print("Verifying Dashboard Logic...")
    
    # Simulate Employee Dashboard Query (Recent Packages)
    recent_packages = db.session.execute(
        db.select(models.Package).order_by(models.Package.created_at.desc()).limit(5)
    ).scalars().all()
    
    print(f"Found {len(recent_packages)} packages.")
    
    for pkg in recent_packages:
        print(f"--- Package {pkg.tracking_number} ---")
        try:
            # Access fields used in dashboard_employee.html
            tracking = pkg.tracking_number
            sender_name = pkg.sender.full_name
            recipient = pkg.recipient_name
            status_label = pkg.status_label
            
            print(f"Tracking: {tracking}")
            print(f"Sender: {sender_name}")
            print(f"Recipient: {recipient}")
            print(f"Status: {status_label}")
            print("Verified successfully.")
        except Exception as e:
            print(f"ERROR displaying package {pkg.tracking_number}: {e}")
            
    print("Verification Complete.")
