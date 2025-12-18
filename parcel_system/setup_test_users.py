from app import create_app, db, models

app = create_app()

with app.app_context():
    # Helper to clean up
    # db.session.query(models.User).delete()
    # db.session.commit()

    # Create Contract User
    u1 = db.session.execute(db.select(models.User).filter_by(username='contract')).scalar_one_or_none()
    if not u1:
        u1 = models.Customer(username='contract', full_name='Contract User', email='c@test.com', phone='123', role=models.UserRole.CUSTOMER, customer_type=models.CustomerType.CONTRACT)
        u1.set_password('123456')
        db.session.add(u1)
        print("Created contract user")

    # Create Prepaid User
    u2 = db.session.execute(db.select(models.User).filter_by(username='prepaid')).scalar_one_or_none()
    if not u2:
        u2 = models.Customer(username='prepaid', full_name='Prepaid User', email='p@test.com', phone='123', role=models.UserRole.CUSTOMER, customer_type=models.CustomerType.PREPAID, balance=1000.0)
        u2.set_password('123456')
        db.session.add(u2)
        print("Created prepaid user")

    # Create Normal User
    u3 = db.session.execute(db.select(models.User).filter_by(username='normal')).scalar_one_or_none()
    if not u3:
        u3 = models.Customer(username='normal', full_name='Normal User', email='n@test.com', phone='123', role=models.UserRole.CUSTOMER, customer_type=models.CustomerType.NON_CONTRACT)
        u3.set_password('123456')
        db.session.add(u3)
        print("Created normal user")
    
    db.session.commit()
    print("Users setup complete.")
