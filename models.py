import enum
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date

# Initialize the Database object (to be used in app.py)
db = SQLAlchemy()
# Define the Employee model
class GenderEnum(enum.Enum):
    Male = "Male"
    Female = "Female"
    Other = "Other"

class roleStatus(enum.Enum):
    admin = 'admin'
    employee = 'employee'

    
# Define the Attendance choices
class AttendanceStatus(enum.Enum):
    Present = "Present"
    Absent = "Absent"
    Late = "Late"
    Leave = "Leave"


class employees(db.Model):
    __tablename__ = "employees"
    emp_id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    name = db.Column(db.String(100), nullable = False)
    email = db.Column(db.String(200), unique = True, nullable= False)
    dob = db.Column(db.Date, nullable = False)
    department = db.Column(db.String(50))
    salary = db.Column(db.Numeric(10,2))
    date_joined = db.Column(db.Date, server_default = db.func.current_date())
    gender = db.Column(db.Enum(GenderEnum, name = 'gender_enum'), nullable = False)
   
class users(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    emp_id = db.Column (db.Integer, db.ForeignKey('employees.emp_id'), unique = True, nullable = False)
    username = db.Column(db.String(50), unique = True, nullable = False)
    password_hash = db.Column(db.String(255), nullable = False)
    role = db.Column(db.Enum(roleStatus, name = 'role_enum'), nullable = False, default = roleStatus.employee)
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class attendance(db.Model):
    __tablename__ = "attendance"
    id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    emp_id = db.Column (db.Integer, db.ForeignKey('employees.emp_id'), nullable = False )
    work_date = db.Column(db.Date, nullable = False , default = date.today )
    status = db.Column(db.Enum('Present', 'Absent', 'Late', 'Leave', name = 'attendance_status_enum'), nullable=False, default='Present')