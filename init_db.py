from app import app, db, User

with app.app_context():
    # Create all tables
    db.create_all()
    
    # Check if admin already exists
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        # Create default admin user
        admin = User(
            username='admin',
            full_name='Administrator',
            role='admin',
            designation='System Administrator'
        )
        admin.set_password('admin123')  # Change this password after first login!
        db.session.add(admin)
        db.session.commit()
        print("✓ Database initialized successfully!")
        print("✓ Default admin user created:")
        print("  Username: admin")
        print("  Password: admin123")
        print("\n⚠ IMPORTANT: Change the admin password after first login!")
    else:
        print("Admin user already exists.")
