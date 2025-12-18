from flask import Flask
from .extensions import db

def create_app(test_config=None):
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'dev_secret_key_123' # Change for production
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parcel_system.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    with app.app_context():
        # Import models here to ensure they are registered with SQLAlchemy
        from . import models
        db.create_all()
        
        # Initialize some seed data if empty
        if not db.session.execute(db.select(models.User)).first():
            print("Initializing seed data...")
            # Create Admin
            admin = models.Employee(
                username='admin',
                full_name='系統管理員',
                email='admin@system.com',
                phone='0900000000',
                role=models.UserRole.ADMIN,
                department='IT'
            )
            admin.set_password('admin123')
            db.session.add(admin)

            # Create Warehouse Staff
            warehouse = models.Employee(
                username='warehouse',
                full_name='倉儲人員',
                email='warehouse@system.com',
                phone='0900000001',
                role=models.UserRole.WAREHOUSE,
                department='Logistics'
            )
            warehouse.set_password('warehouse123')
            db.session.add(warehouse)

            # Create Driver
            driver = models.Employee(
                username='driver',
                full_name='物流司機',
                email='driver@system.com',
                phone='0900000002',
                role=models.UserRole.DRIVER,
                department='Transport'
            )
            driver.set_password('driver123')
            db.session.add(driver)

            # Create Customer Service
            cs = models.Employee(
                username='cs',
                full_name='客服人員',
                email='cs@system.com',
                phone='0900000003',
                role=models.UserRole.CS,
                department='Support'
            )
            cs.set_password('cs123')
            db.session.add(cs)
            
            # Create Pricing Rules
            rules = [
                models.PricingRule(service_type=models.DeliverySpeed.STANDARD, base_rate=100, rate_per_kg=10),
                models.PricingRule(service_type=models.DeliverySpeed.OVERNIGHT, base_rate=200, rate_per_kg=20),
                models.PricingRule(service_type=models.DeliverySpeed.TWO_DAY, base_rate=150, rate_per_kg=15),
                models.PricingRule(service_type=models.DeliverySpeed.ECONOMY, base_rate=80, rate_per_kg=5),
            ]
            db.session.add_all(rules)
            db.session.commit()

    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app
