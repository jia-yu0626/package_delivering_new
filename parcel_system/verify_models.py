
from app import create_app, db, models

def verify_models():
    app = create_app()
    with app.app_context():
        try:
            # Try to access properties to ensure classes are loaded
            print("Verifying User model...")
            assert hasattr(models.User, 'username')
            print("Verifying Customer model...")
            assert hasattr(models.Customer, 'balance')
            print("Verifying Package model...")
            assert hasattr(models.Package, 'tracking_number')
            print("Verifying WarehouseStaff model...")
            assert hasattr(models.WarehouseStaff, 'warehouse_location_id')
            
            # Create tables to check for schema errors
            db.create_all()
            print("Database tables created successfully.")
            
            print("Models verification passed!")
        except Exception as e:
            print(f"Verification Failed: {e}")
            raise

if __name__ == "__main__":
    verify_models()
