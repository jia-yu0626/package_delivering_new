from app import create_app, models, db
import sys

app = create_app()

with app.app_context():
    users = db.session.query(models.User).all()
    print(f"Total users: {len(users)}")
    for u in users:
        print(f"User: {u.username}, Role: {u.role}")
