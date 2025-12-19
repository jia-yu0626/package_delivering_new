from app import create_app, db, models

app = create_app()

with app.app_context():
    admin = db.session.execute(db.select(models.User).filter_by(username='admin')).scalar_one_or_none()
    if not admin:
        admin = models.Employee(
            username='admin', 
            full_name='System Administrator', 
            email='admin@test.com', 
            phone='0000000000', 
            role=models.UserRole.ADMIN,
            department='Management'
        )
        admin.set_password('123456')
        db.session.add(admin)
        db.session.commit()
        print("Created Admin user: admin / 123456")
    else:
        print("Admin user already exists")
