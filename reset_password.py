from app import app, db, User
import sys

def reset_password(username, new_password):
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if user:
            user.set_password(new_password)
            db.session.commit()
            print(f"✓ Password reset successfully for user: {username}")
            return True
        else:
            print(f"✗ User '{username}' not found!")
            return False

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("\nUsage: python reset_password.py <username> <new_password>")
        print("\nExample: python reset_password.py admin newpass123")
        print("\nAvailable users:")
        with app.app_context():
            users = User.query.all()
            for user in users:
                print(f"  - {user.username} ({user.role})")
    else:
        username = sys.argv[1]
        new_password = sys.argv[2]
        reset_password(username, new_password)
