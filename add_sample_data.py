from app import app, db, User, Leave, Attendance
from datetime import date, datetime, timedelta
import random

with app.app_context():
    # Add sample employees
    employees_data = [
        {'username': 'john.doe', 'full_name': 'John Doe', 'designation': 'Software Engineer', 'department': 'IT', 'role': 'employee'},
        {'username': 'jane.smith', 'full_name': 'Jane Smith', 'designation': 'HR Manager', 'department': 'HR', 'role': 'supervisor'},
        {'username': 'mike.wilson', 'full_name': 'Mike Wilson', 'designation': 'Sales Executive', 'department': 'Sales', 'role': 'employee'},
        {'username': 'sarah.johnson', 'full_name': 'Sarah Johnson', 'designation': 'Accountant', 'department': 'Finance', 'role': 'employee'},
        {'username': 'david.brown', 'full_name': 'David Brown', 'designation': 'Marketing Manager', 'department': 'Marketing', 'role': 'supervisor'},
    ]
    
    emp_counter = 2
    for emp_data in employees_data:
        existing = User.query.filter_by(username=emp_data['username']).first()
        if not existing:
            emp = User(
                username=emp_data['username'],
                full_name=emp_data['full_name'],
                designation=emp_data['designation'],
                department=emp_data['department'],
                role=emp_data['role'],
                emp_number=f'EMP{str(emp_counter).zfill(3)}',
                doj=date.today() - timedelta(days=random.randint(30, 365)),
                team='corporate',
                salary=random.randint(30000, 80000),
                probation_completed=True
            )
            emp.set_password('password123')
            db.session.add(emp)
            emp_counter += 1
    
    db.session.commit()
    print(f"Added {len(employees_data)} sample employees!")
    
    # Add some attendance records
    employees = User.query.filter_by(role='employee').all()
    today = date.today()
    for emp in employees:
        for i in range(5):
            att_date = today - timedelta(days=i)
            existing_att = Attendance.query.filter_by(user_id=emp.id, date=att_date).first()
            if not existing_att:
                att = Attendance(
                    user_id=emp.id,
                    date=att_date,
                    in_time=datetime.strptime('09:00', '%H:%M').time(),
                    out_time=datetime.strptime('18:00', '%H:%M').time(),
                    overtime=0.0
                )
                db.session.add(att)
    
    db.session.commit()
    print("Added attendance records!")
    
    # Add some pending leaves
    if employees:
        leave = Leave(
            user_id=employees[0].id,
            leave_type='casual',
            start_date=today + timedelta(days=2),
            end_date=today + timedelta(days=3),
            status='pending',
            reason='Personal work'
        )
        db.session.add(leave)
        db.session.commit()
        print("Added sample leave request!")
    
    print("\nSample data added successfully!")
    print("You can login with:")
    print("Username: admin, Password: admin123")
    print("Or any employee: username (e.g., john.doe), Password: password123")
