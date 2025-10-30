from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, date, timedelta
import os
import sys
import logging
from sqlalchemy import func, extract
from datetime import date
from sqlalchemy import func

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_secret_key_here')  # Change to a secure random key

# MySQL Configuration
# Format: mysql+pymysql://username:password@host:port/database
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'mysql+pymysql://root:1234@localhost:3306/office_management'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', '/tmp/uploads')
app.config['LOG_FOLDER'] = os.environ.get('LOG_FOLDER', '/tmp/logs')

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Create directories only if they don't exist (serverless-friendly)
try:
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['LOG_FOLDER'], exist_ok=True)
except:
    pass  # Ignore errors in serverless environment

# Daily Logger
def get_daily_logger():
    today = datetime.now().strftime('%Y-%m-%d')
    log_file = os.path.join(app.config['LOG_FOLDER'], f'{today}.log')
    logger = logging.getLogger('daily_logger')
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        try:
            handler = logging.FileHandler(log_file)
        except Exception:
            # Fallback to stdout if file writing is not permitted (e.g., serverless)
            handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(asctime)s - %(user)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

# Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    full_name = db.Column(db.String(100))
    designation = db.Column(db.String(100))
    probation_completed = db.Column(db.Boolean, default=False)
    emp_number = db.Column(db.String(20), unique=True)
    doj = db.Column(db.Date)
    perm_address = db.Column(db.Text)
    curr_address = db.Column(db.Text)
    emerg_contact_name = db.Column(db.String(100))
    emerg_contact_num = db.Column(db.String(20))
    birth_date = db.Column(db.Date)
    pan = db.Column(db.String(20))
    aadhar = db.Column(db.String(20))
    role = db.Column(db.Enum('employee', 'supervisor', 'admin'), default='employee')
    manager_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    department = db.Column(db.String(100))
    team = db.Column(db.Enum('corporate', 'production'))
    profile_picture = db.Column(db.String(200))
    last_working_day = db.Column(db.Date)
    salary = db.Column(db.Float)
    comment = db.Column(db.Text)

    assigned_employees = db.relationship('User', backref=db.backref('manager', remote_side=[id]))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_leave_balance(self, leave_type, year=None):
        if year is None:
            year = datetime.now().year
        start_of_year = date(year, 1, 1)
        end_of_year = date(year, 12, 31)
        approved_leaves = Leave.query.filter_by(user_id=self.id, leave_type=leave_type, status='approved').filter(
            Leave.start_date >= start_of_year, Leave.start_date <= end_of_year
        ).all()
        used_days = sum((l.end_date - l.start_date).days + 1 for l in approved_leaves)
        
        if leave_type == 'casual':
            entitlement = 7
            return entitlement - used_days
        elif leave_type == 'sick':
            entitlement = 7
            # Carry forward: Get previous year balance
            prev_balance = self.get_leave_balance('sick', year-1) if year > 2020 else 0
            carried = min(prev_balance, 30) if prev_balance > 0 else 0
            return entitlement + carried - used_days
        elif leave_type == 'earned':
            # Approximate: days worked / 20
            if not self.doj:
                return 0
            days_worked = (date.today() - self.doj).days
            entitlement = days_worked // 20
            accumulated = min(entitlement - used_days, 90)
            return accumulated
        elif leave_type == 'maternity':
            return 84 if self.team == 'corporate' else 0
        else:
            return 0  # LOP unlimited

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    in_time = db.Column(db.Time)
    out_time = db.Column(db.Time)
    overtime = db.Column(db.Float, default=0.0)

    user = db.relationship('User', backref='attendances')

class Leave(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    leave_type = db.Column(db.Enum('casual', 'sick', 'earned', 'maternity', 'lop'), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.Enum('pending', 'approved', 'rejected'), default='pending')
    reason = db.Column(db.Text)
    doctor_cert = db.Column(db.String(200))

    user = db.relationship('User', backref='leaves')

class Holiday(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    name = db.Column(db.String(100))

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    file_path = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100))

    user = db.relationship('User', backref='documents')

class SalarySlip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    file_path = db.Column(db.String(200), nullable=False)

    user = db.relationship('User', backref='salary_slips')

class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    action = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='logs')

# 1. Add Task Model
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    assigned_to = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assigned_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.Enum('pending', 'in_progress', 'completed', 'overdue'), default='pending')
    progress = db.Column(db.Integer, default=0)  # 0-100
    due_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    assigned_user = db.relationship('User', foreign_keys=[assigned_to])
    assigned_by_user = db.relationship('User', foreign_keys=[assigned_by])

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def log_action(action):
    logger = get_daily_logger()
    username = current_user.username if current_user.is_authenticated else 'anonymous'
    logger.info(action, extra={'user': username})
    if current_user.is_authenticated:
        new_log = Log(user_id=current_user.id, action=action)
        db.session.add(new_log)
        db.session.commit()

# Context processor for common template variables
@app.context_processor
def inject_common_vars():
    return {
        'today': date.today().strftime('%B %d, %Y')
    }

# Routes
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        print(f"\n=== LOGIN ATTEMPT ===")
        print(f"Username: {username}")
        print(f"Password: {password}")
        
        user = User.query.filter_by(username=username).first()
        print(f"User found: {user is not None}")
        
        if user:
            print(f"User role: {user.role}")
            password_check = user.check_password(password)
            print(f"Password check result: {password_check}")
            
            if password_check:
                login_user(user)
                print(f"Login successful! Redirecting to dashboard...")
                log_action('Logged in')
                return redirect(url_for('dashboard'))
        
        print("Login failed - Invalid credentials")
        flash('Invalid credentials', 'danger')
        log_action(f'Failed login attempt for {username}')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    log_action('Logged out')
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif current_user.role == 'supervisor':
        return redirect(url_for('supervisor_dashboard'))
    else:
        return redirect(url_for('employee_dashboard'))

# Employee Routes
@app.route('/employee/dashboard')
@login_required
def employee_dashboard():
    if current_user.role != 'employee':
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    
    today = date.today()
    
    # Check today's attendance
    my_att_today = Attendance.query.filter_by(user_id=current_user.id, date=today).first()
    today_attendance = 'Present' if my_att_today else 'Absent'
    
    # Pending leaves count
    my_pending_leaves = Leave.query.filter_by(user_id=current_user.id, status='pending').count()
    
    # Salary slips count
    salary_slips_count = SalarySlip.query.filter_by(user_id=current_user.id).count()
    
    log_action('Viewed employee dashboard')
    
    return render_template('employee_dashboard.html',
                         today_attendance=today_attendance,
                         my_pending_leaves=my_pending_leaves,
                         salary_slips_count=salary_slips_count)

@app.route('/employee/attendance', methods=['GET', 'POST'])
@login_required
def employee_attendance():
    if current_user.role != 'employee':
        return redirect(url_for('dashboard'))
    month = int(request.form.get('month', datetime.now().month))
    year = int(request.form.get('year', datetime.now().year))
    attendances = Attendance.query.filter_by(user_id=current_user.id).filter(
        db.extract('month', Attendance.date) == month,
        db.extract('year', Attendance.date) == year
    ).all()
    log_action('Viewed attendance')
    return render_template('employee_attendance.html', attendances=attendances, month=month, year=year)

@app.route('/employee/apply_leave', methods=['GET', 'POST'])
@login_required
def apply_leave():
    if current_user.role != 'employee':
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        leave_type = request.form['leave_type']
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
        reason = request.form['reason']
        days = (end_date - start_date).days + 1
        
        # Check leave balance
        balance = current_user.get_leave_balance(leave_type)
        if leave_type != 'lop' and days > balance:
            flash(f'Insufficient {leave_type} leave balance ({balance} days available)', 'warning')
            return render_template('apply_leave.html')
        
        # Policy validations
        if leave_type == 'casual' and days > 3:
            flash('Casual leave cannot exceed 3 days without management approval', 'warning')
            return render_template('apply_leave.html')
        
        if leave_type == 'sick' and days > 2 and not request.files.get('doctor_cert'):
            flash('Sick leave >2 days requires doctor certificate', 'warning')
            return render_template('apply_leave.html')
        
        new_leave = Leave(user_id=current_user.id, leave_type=leave_type, start_date=start_date, end_date=end_date, reason=reason)
        
        # Handle doctor certificate upload
        if 'doctor_cert' in request.files:
            file = request.files['doctor_cert']
            if file and file.filename:
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                new_leave.doctor_cert = file_path
        
        db.session.add(new_leave)
        db.session.commit()
        log_action(f'Applied for {leave_type} leave')
        flash('Leave applied successfully', 'success')
    return render_template('apply_leave.html')

@app.route('/employee/profile')
@login_required
def employee_profile():
    if current_user.role != 'employee':
        return redirect(url_for('dashboard'))
    log_action('Viewed profile')
    return render_template('employee_profile.html', user=current_user)

@app.route('/employee/salary_slips')
@login_required
def employee_salary_slips():
    if current_user.role != 'employee':
        return redirect(url_for('dashboard'))
    slips = SalarySlip.query.filter_by(user_id=current_user.id).all()
    log_action('Viewed salary slips')
    return render_template('employee_salary_slips.html', slips=slips)

@app.route('/download/salary_slip/<int:slip_id>')
@login_required
def download_salary_slip(slip_id):
    slip = SalarySlip.query.get_or_404(slip_id)
    if slip.user_id != current_user.id and current_user.role not in ['supervisor', 'admin']:
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    log_action(f'Downloaded salary slip {slip_id}')
    return send_file(slip.file_path, as_attachment=True)

@app.route('/employee/documents')
@login_required
def employee_documents():
    if current_user.role != 'employee':
        return redirect(url_for('dashboard'))
    docs = Document.query.filter_by(user_id=current_user.id).all()
    log_action('Viewed documents')
    return render_template('employee_documents.html', docs=docs)

@app.route('/download/document/<int:doc_id>')
@login_required
def download_document(doc_id):
    doc = Document.query.get_or_404(doc_id)
    if doc.user_id != current_user.id and current_user.role not in ['supervisor', 'admin']:
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    log_action(f'Downloaded document {doc_id}')
    return send_file(doc.file_path, as_attachment=True)

@app.route('/employee/holidays')
@login_required
def employee_holidays():
    holidays = Holiday.query.all()
    log_action('Viewed holidays')
    return render_template('holidays.html', holidays=holidays)

# Supervisor Routes
@app.route('/supervisor/dashboard')
@login_required
def supervisor_dashboard():
    if current_user.role != 'supervisor':
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    
    assigned = current_user.assigned_employees
    today = date.today()
    
    # Get assigned employee IDs
    assigned_ids = [e.id for e in assigned]
    
    # Calculate team statistics
    pending_my_leaves = Leave.query.filter(
        Leave.user_id.in_(assigned_ids),
        Leave.status == 'pending'
    ).count() if assigned_ids else 0
    
    team_attendance_today = Attendance.query.filter(
        Attendance.user_id.in_(assigned_ids),
        Attendance.date == today
    ).count() if assigned_ids else 0
    
    team_overtime = db.session.query(func.sum(Attendance.overtime)).filter(
        Attendance.user_id.in_(assigned_ids),
        Attendance.date == today
    ).scalar() or 0
    
    # Additional supervisor-specific reports
    team_pending_leaves = Leave.query.filter(
        Leave.user_id.in_(assigned_ids),
        Leave.status == 'pending'
    ).all() if assigned_ids else []
    
    team_approved_leaves = Leave.query.filter(
        Leave.user_id.in_(assigned_ids),
        Leave.status == 'approved'
    ).count() if assigned_ids else 0
    
    team_absent_today = len(assigned) - team_attendance_today if assigned else 0
    
    avg_team_overtime = team_overtime / len(assigned) if assigned and team_overtime > 0 else 0
    
    # Mock team progress (can be replaced with real Goal model queries)
    team_progress_avg = 0
    
    # Mock attendance data for chart (replace with actual query)
    attendance_monthly = [5, 6, 8, 7, 9]
    
    log_action('Viewed supervisor dashboard')
    
    return render_template('supervisor_dashboard.html', 
                         assigned=assigned,
                         pending_my_leaves=pending_my_leaves,
                         team_attendance_today=team_attendance_today,
                         team_overtime=team_overtime,
                         team_pending_leaves=team_pending_leaves,
                         team_approved_leaves=team_approved_leaves,
                         team_absent_today=team_absent_today,
                         avg_team_overtime=avg_team_overtime,
                         team_progress_avg=team_progress_avg,
                         attendance_monthly=attendance_monthly)

@app.route('/supervisor/employee/<int:emp_id>/info')
@login_required
def supervisor_employee_info(emp_id):
    if current_user.role != 'supervisor':
        return redirect(url_for('dashboard'))
    emp = User.query.get_or_404(emp_id)
    if emp.manager_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    log_action(f'Viewed info for employee {emp_id}')
    return render_template('employee_info.html', emp=emp)

@app.route('/supervisor/employee/<int:emp_id>/attendance', methods=['GET', 'POST'])
@login_required
def supervisor_employee_attendance(emp_id):
    if current_user.role != 'supervisor':
        return redirect(url_for('dashboard'))
    emp = User.query.get_or_404(emp_id)
    if emp.manager_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        att_id = request.form.get('att_id')
        if att_id:
            att = Attendance.query.get(att_id)
            if att:
                att.in_time = datetime.strptime(request.form['in_time'], '%H:%M').time()
                att.out_time = datetime.strptime(request.form['out_time'], '%H:%M').time()
                att.overtime = float(request.form['ot'])
                db.session.commit()
                log_action(f'Updated attendance {att_id} for employee {emp_id}')
                flash('Attendance updated', 'success')
        else:
            date_str = request.form['date']
            in_time = request.form['in_time']
            out_time = request.form['out_time']
            ot = float(request.form['ot'])
            new_att = Attendance(user_id=emp_id, date=datetime.strptime(date_str, '%Y-%m-%d').date(),
                                 in_time=datetime.strptime(in_time, '%H:%M').time(),
                                 out_time=datetime.strptime(out_time, '%H:%M').time(), overtime=ot)
            db.session.add(new_att)
            db.session.commit()
            log_action(f'Added attendance for employee {emp_id}')
            flash('Attendance added', 'success')
    attendances = Attendance.query.filter_by(user_id=emp_id).all()
    return render_template('edit_attendance.html', attendances=attendances, emp=emp)

@app.route('/supervisor/employee/<int:emp_id>/leaves', methods=['GET', 'POST'])
@login_required
def supervisor_employee_leaves(emp_id):
    if current_user.role != 'supervisor':
        return redirect(url_for('dashboard'))
    emp = User.query.get_or_404(emp_id)
    if emp.manager_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        leave_id = request.form['leave_id']
        status = request.form['status']
        leave = Leave.query.get(leave_id)
        if leave:
            leave.status = status
            db.session.commit()
            log_action(f'Updated leave {leave_id} status to {status} for employee {emp_id}')
            flash('Leave status updated', 'success')
    leaves = Leave.query.filter_by(user_id=emp_id).all()
    return render_template('edit_leaves.html', leaves=leaves, emp=emp)

# Admin Routes
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    
    today = date.today()
    
    employees = User.query.filter_by(role='employee').all()
    supervisors = User.query.filter_by(role='supervisor').all()
    
    # Calculate dashboard metrics
    leaves_today = Leave.query.filter(
        Leave.start_date <= today,
        Leave.end_date >= today,
        Leave.status == 'approved'
    ).count()
    
    departments = {u.department for u in User.query.all() if u.department}
    pending_leaves = Leave.query.filter_by(status='pending').count()
    present_today = Attendance.query.filter_by(date=today).count()
    approved_leaves_count = Leave.query.filter_by(status='approved').count()
    
    holiday_count = Holiday.query.count()
    log_count = Log.query.count()
    
    log_action('Viewed admin dashboard')
    
    return render_template('admin_dashboard.html', 
                         employees=employees,
                         supervisors=supervisors,
                         leaves_today=leaves_today,
                         departments=departments,
                         pending_leaves=pending_leaves,
                         present_today=present_today,
                         approved_leaves_count=approved_leaves_count,
                         holiday_count=holiday_count,
                         log_count=log_count)

@app.route('/admin/holidays', methods=['GET', 'POST'])
@login_required
def admin_holidays():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        date_str = request.form['date']
        name = request.form['name']
        new_holiday = Holiday(date=datetime.strptime(date_str, '%Y-%m-%d').date(), name=name)
        db.session.add(new_holiday)
        db.session.commit()
        log_action(f'Added holiday {name}')
        flash('Holiday added', 'success')
    holidays = Holiday.query.all()
    return render_template('admin_holidays.html', holidays=holidays)

@app.route('/admin/logs', methods=['GET', 'POST'])
@login_required
def admin_logs():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    date_str = request.form.get('date', datetime.now().strftime('%Y-%m-%d'))
    logs = Log.query.filter(db.func.date(Log.timestamp) == date_str).all()
    log_action('Viewed logs')
    return render_template('admin_logs.html', logs=logs, date=date_str)

# Example upload route for admin (expand for salary slips, profile pic, etc.)
@app.route('/admin/upload_document/<int:emp_id>', methods=['POST'])
@login_required
def upload_document(emp_id):
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    file = request.files['file']
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        name = request.form['name']
        new_doc = Document(user_id=emp_id, file_path=file_path, name=name)
        db.session.add(new_doc)
        db.session.commit()
        log_action(f'Uploaded document for employee {emp_id}')
        flash('Document uploaded', 'success')
    return redirect(url_for('admin_dashboard'))

# Employee: View leave balances
@app.route('/employee/leave_balances')
@login_required
def employee_leave_balances():
    if current_user.role != 'employee':
        return redirect(url_for('dashboard'))
    balances = {
        'casual': current_user.get_leave_balance('casual'),
        'sick': current_user.get_leave_balance('sick'),
        'earned': current_user.get_leave_balance('earned'),
        'maternity': current_user.get_leave_balance('maternity'),
    }
    log_action('Viewed leave balances')
    return render_template('employee_leave_balances.html', balances=balances)

# Admin: Manage users
@app.route('/admin/users', methods=['GET', 'POST'])
@login_required
def admin_users():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        full_name = request.form['full_name']
        role = request.form['role']
        new_user = User(username=username, full_name=full_name, role=role)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        log_action(f'Created user {username}')
        flash('User created', 'success')
    users = User.query.all()
    return render_template('admin_users.html', users=users)

@app.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        user.full_name = request.form['full_name']
        user.designation = request.form['designation']
        user.manager_id = int(request.form['manager_id']) if request.form['manager_id'] else None
        db.session.commit()
        log_action(f'Edited user {user.username}')
        flash('User updated', 'success')
    supervisors = User.query.filter_by(role='supervisor').all()
    return render_template('admin_edit_user.html', user=user, supervisors=supervisors)

# Add route for delete confirmation
@app.route('/admin/delete_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def admin_delete_user(user_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    # Prevent self-deletion
    if user.id == current_user.id:
        flash('You cannot delete your own account!', 'danger')
        return redirect(url_for('admin_users'))
    
    # Prevent deleting the last admin
    if user.role == 'admin':
        admin_count = User.query.filter_by(role='admin').count()
        if admin_count <= 1:
            flash('Cannot delete the last admin account!', 'danger')
            return redirect(url_for('admin_users'))
    
    if request.method == 'POST':
        # Delete related data (cascade or manual)
        Attendance.query.filter_by(user_id=user_id).delete()
        Leave.query.filter_by(user_id=user_id).delete()
        Document.query.filter_by(user_id=user_id).delete()
        SalarySlip.query.filter_by(user_id=user_id).delete()
        Log.query.filter_by(user_id=user_id).delete()
        
        # Reassign managed employees to None or another manager
        User.query.filter_by(manager_id=user_id).update({'manager_id': None})
        
        db.session.delete(user)
        db.session.commit()
        
        log_action(f'Deleted user {user.username} (ID: {user_id})')
        flash(f'User {user.full_name} deleted successfully!', 'success')
        return redirect(url_for('admin_users'))
    
    return render_template('admin_delete_user.html', user=user)

# Admin Attendance Dashboard
@app.route('/admin/attendance_dashboard')
@login_required
def admin_attendance_dashboard():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))
    month = datetime.now().month
    year = datetime.now().year
    total_attendances = db.session.query(func.count(Attendance.id)).filter(
        extract('month', Attendance.date) == month,
        extract('year', Attendance.date) == year
    ).scalar()
    total_overtime = db.session.query(func.sum(Attendance.overtime)).filter(
        extract('month', Attendance.date) == month,
        extract('year', Attendance.date) == year
    ).scalar() or 0
    log_action('Viewed attendance dashboard')
    return render_template('admin_attendance_dashboard.html', total_attendances=total_attendances, total_overtime=total_overtime, month=month, year=year)

# Manager Team List View
@app.route('/supervisor/team_list')
@login_required
def supervisor_team_list():
    if current_user.role != 'supervisor':
        return redirect(url_for('dashboard'))
    
    team = current_user.assigned_employees
    # Get stats for each employee
    team_stats = []
    for emp in team:
        stats = {
            'employee': emp,
            'today_attendance': Attendance.query.filter_by(user_id=emp.id, date=date.today()).first(),
            'pending_leaves': Leave.query.filter_by(user_id=emp.id, status='pending').count(),
            'tasks_pending': Task.query.filter_by(assigned_to=emp.id, status='pending').count(),
            'tasks_overdue': Task.query.filter_by(assigned_to=emp.id, status__not_in=['completed'], due_date__lt=date.today()).count(),
        }
        team_stats.append(stats)
    
    return render_template('supervisor_team_list.html', team_stats=team_stats)

# 4. Assign Task
@app.route('/supervisor/assign_task/<int:emp_id>', methods=['GET', 'POST'])
@login_required
def assign_task(emp_id):
    if current_user.role != 'supervisor':
        return redirect(url_for('dashboard'))
    
    emp = User.query.get_or_404(emp_id)
    if emp.manager_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('supervisor_team_list'))
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        due_date = datetime.strptime(request.form['due_date'], '%Y-%m-%d').date()
        
        new_task = Task(
            title=title,
            description=description,
            assigned_to=emp_id,
            assigned_by=current_user.id,
            due_date=due_date
        )
        db.session.add(new_task)
        db.session.commit()
        flash('Task assigned successfully!', 'success')
        log_action(f'Assigned task "{title}" to {emp.full_name}')
        return redirect(url_for('supervisor_employee_tasks', emp_id=emp_id))
    
    return render_template('assign_task.html', employee=emp)

# 5. Employee Tasks View (Manager)
@app.route('/supervisor/employee/<int:emp_id>/tasks')
@login_required
def supervisor_employee_tasks(emp_id):
    if current_user.role != 'supervisor':
        return redirect(url_for('dashboard'))
    
    emp = User.query.get_or_404(emp_id)
    if emp.manager_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('supervisor_team_list'))
    
    tasks = Task.query.filter_by(assigned_to=emp_id).order_by(Task.due_date).all()
    return render_template('employee_tasks.html', employee=emp, tasks=tasks)

# 6. Update Task Progress/Status
@app.route('/supervisor/task/<int:task_id>/update', methods=['POST'])
@login_required
def update_task(task_id):
    if current_user.role != 'supervisor':
        return redirect(url_for('dashboard'))
    
    task = Task.query.get_or_404(task_id)
    if task.assigned_by != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('supervisor_team_list'))
    
    if 'status' in request.form:
        task.status = request.form['status']
    if 'progress' in request.form:
        task.progress = int(request.form['progress'])
    
    db.session.commit()
    flash('Task updated successfully!', 'success')
    log_action(f'Updated task {task_id} status/progress')
    return redirect(request.referrer or url_for('supervisor_team_list'))

# 7. Employee Update (Manager can update profile)
@app.route('/supervisor/employee/<int:emp_id>/update', methods=['GET', 'POST'])
@login_required
def supervisor_update_employee(emp_id):
    if current_user.role != 'supervisor':
        return redirect(url_for('dashboard'))
    
    emp = User.query.get_or_404(emp_id)
    if emp.manager_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('supervisor_team_list'))
    
    if request.method == 'POST':
        emp.full_name = request.form['full_name']
        emp.designation = request.form['designation']
        emp.department = request.form['department']
        emp.salary = float(request.form['salary']) if request.form['salary'] else emp.salary
        emp.comment = request.form['comment']
        db.session.commit()
        flash('Employee updated successfully!', 'success')
        log_action(f'Updated employee {emp_id}')
        return redirect(url_for('supervisor_team_list'))
    
    return render_template('update_employee.html', employee=emp)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
