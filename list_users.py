"""List all users in the database"""
from app import app, db, User

with app.app_context():
    users = User.query.all()
    if users:
        print(f"\n{'='*60}")
        print(f"TOTAL USERS: {len(users)}")
        print(f"{'='*60}\n")
        for user in users:
            print(f"Username: {user.username:15s} | Role: {user.role:10s} | Name: {user.full_name or 'N/A'}")
        print(f"\n{'='*60}\n")
    else:
        print("\n❌ No users found in database!\n")
