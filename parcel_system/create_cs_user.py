from app import create_app, db, models

app = create_app()

with app.app_context():
    cs = db.session.execute(db.select(models.User).filter_by(username='cs_user')).scalar_one_or_none()
    if not cs:
        cs = models.Employee(
            username='cs_user', 
            full_name='CS Representative', 
            email='cs@test.com', 
            phone='777888999', 
            role=models.UserRole.CS,
            department='Customer Service'
        )
        cs.set_password('123456')
        db.session.add(cs)
        db.session.commit()
        print("Created CS user: cs_user / 123456")
    else:
        print("CS user already exists")
