from app import create_app, models, db
from app.models import UserRole

app = create_app()

def create_user_if_not_exists(username, password, full_name, email, phone, role, department=None):
    user = db.session.query(models.User).filter_by(username=username).first()
    if user:
        print(f"User {username} already exists.")
    else:
        print(f"Creating user {username}...")
        if role == UserRole.CUSTOMER:
            new_user = models.Customer(
                username=username,
                full_name=full_name,
                email=email,
                phone=phone,
                role=role
            )
        else:
            new_user = models.Employee(
                username=username,
                full_name=full_name,
                email=email,
                phone=phone,
                role=role,
                department=department
            )
        new_user.set_password(password)
        db.session.add(new_user)

with app.app_context():
    # System Administrator
    create_user_if_not_exists(
        username='admin', 
        password='admin123',
        full_name='系統管理員',
        email='admin@system.com',
        phone='0900000000',
        role=UserRole.ADMIN,
        department='IT'
    )

    # Driver
    create_user_if_not_exists(
        username='driver',
        password='driver123',
        full_name='物流司機',
        email='driver@system.com',
        phone='0900000002',
        role=UserRole.DRIVER,
        department='Transport'
    )

    # Warehouse
    create_user_if_not_exists(
        username='warehouse',
        password='warehouse123',
        full_name='倉儲人員',
        email='warehouse@system.com',
        phone='0900000001',
        role=UserRole.WAREHOUSE,
        department='Logistics'
    )

    # Customer Service
    create_user_if_not_exists(
        username='cs',
        password='cs123',
        full_name='客服人員',
        email='cs@system.com',
        phone='0900000003',
        role=UserRole.CS,
        department='Support'
    )

    # Test Customer
    create_user_if_not_exists(
        username='customer',
        password='customer123',
        full_name='測試客戶',
        email='customer@system.com',
        phone='0900000004',
        role=UserRole.CUSTOMER
    )

    db.session.commit()
    print("Users check/creation complete.")
