# MySQL Setup Instructions

## Step 1: Install Required Python Packages
```powershell
pip install pymysql cryptography
```

## Step 2: Create MySQL Database

### Option A: Using MySQL Command Line
```powershell
mysql -u root -p
```

Then run:
```sql
source D:\office_management\setup_mysql.sql
```

### Option B: Import the SQL file directly
```powershell
mysql -u root -p < D:\office_management\setup_mysql.sql
```

### Option C: Run commands manually in MySQL prompt
```sql
CREATE DATABASE IF NOT EXISTS office_management CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE office_management;
```

Then copy/paste the table creation commands from `setup_mysql.sql`.

## Step 3: Configure Database Connection

The app is configured to connect to MySQL with these default settings:
- **Host**: localhost
- **Port**: 3306
- **Username**: root
- **Password**: (empty)
- **Database**: office_management

### To use a different password or user:

**Option 1**: Set environment variable (recommended)
```powershell
$env:DATABASE_URL = "mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/office_management"
```

**Option 2**: Edit `app.py` line 20 directly:
```python
'mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/office_management'
```

## Step 4: Initialize the Database

After MySQL tables are created, run:
```powershell
python D:\office_management\init_db.py
```

This creates the default admin user:
- **Username**: admin
- **Password**: admin123

## Step 5: Start the Application
```powershell
python D:\office_management\app.py
```

## Troubleshooting

### Error: "No module named 'pymysql'"
```powershell
pip install pymysql cryptography
```

### Error: "Access denied for user 'root'@'localhost'"
Update the connection string with your MySQL password:
```powershell
$env:DATABASE_URL = "mysql+pymysql://root:YOUR_MYSQL_PASSWORD@localhost:3306/office_management"
```

### Error: "Can't connect to MySQL server"
Make sure MySQL service is running:
```powershell
# Check if MySQL is running
Get-Service -Name MySQL* | Select-Object Name, Status
```

## Migrate Existing SQLite Data (Optional)

If you want to keep your existing data from SQLite:

1. Export data from SQLite:
```python
# export_sqlite.py
from app import app, db, User, Attendance, Leave, Holiday
import json

with app.app_context():
    users = User.query.all()
    # Export logic here
```

2. Import into MySQL after setup

## Connection String Format

```
mysql+pymysql://username:password@host:port/database_name
```

Examples:
- Local default: `mysql+pymysql://root:@localhost:3306/office_management`
- With password: `mysql+pymysql://root:MyPass123@localhost:3306/office_management`
- Remote server: `mysql+pymysql://user:pass@192.168.1.100:3306/office_management`
