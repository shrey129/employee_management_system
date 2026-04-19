from flask import Flask, render_template, request, redirect, url_for, flash
from models import db, employees, users, attendance, roleStatus, GenderEnum  # Importing my hard work!
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import date
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev_key_123' # You can change this to any random string
# 1. Database Configuration
# using config with my actual MySQL password


# Get the URL from the Environment Variable (Render)
import os

# 1. Get the URL
raw_uri = os.environ.get('DATABASE_URL') or 'postgresql://employee_db_fyrg_user:dbtQehBpsmwaVSMcyKvfK1oq2pN1HvbM@dpg-d7ie05n7f7vs7394ifhg-a/employee_db_fyrg'

# 2. Clean it (Remove accidental spaces or quotes)
uri = raw_uri.strip().replace('"', '').replace("'", "")

# 3. Fix the prefix
if uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

# 4. Assign it
app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# This will help us debug in the Render logs!
print(f"Connecting to database starting with: {uri[:15]}...")

# 2. Initialize the DB with the App
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # The name of your login route function


# 3. Create Tables (The Sync)
# To check models.py and makes sure MySQL has the exact same tables.
with app.app_context():
    db.create_all()
    
    # 1. Check if the employee table is empty
    if not employees.query.first():
        # Create a "dummy" employee for the admin to link to
        admin_emp = employees(
            name="System Admin",
            email="admin@system.com",
            dob=date(1990, 1, 1),
            gender=GenderEnum.Male, # Make sure this matches your Enum class!
            department="IT",
            salary=0
        )
        db.session.add(admin_emp)
        db.session.commit()
        
        # 2. Now create the User linked to that Employee
        if not users.query.filter_by(username='admin').first():
            admin_login = users(
                username='admin', 
                emp_id=admin_emp.emp_id, 
                role=roleStatus.admin
            )
            admin_login.set_password('admin123') # Change this to your preferred password
            db.session.add(admin_login)
            db.session.commit()
            print("Successfully created Admin Employee and User!")

@login_manager.user_loader
def load_user(user_id):
    if user_id is None:
        return None
    try:
        return db.session.get(users,int(user_id))
    except:
        return None
    

#-----------2) Authentication -----------
@app.route('/login', methods = ['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        #looking for user in database
        user = users.query.filter_by(username=username).first()

        #checking if username and password is correct
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
def logout():
  logout_user()
  return redirect(url_for('login'))


# 4. First Route (The Home Page)
@app.route('/')
@login_required 
def index():

    # 1. Look for a search term
    search_query = request.args.get('search')
    
    # 2. START with the base list (Always exclude Ghost Admin 9999)
    query = employees.query.filter(employees.emp_id != 9999)

    # 3. IF searching, add extra "rules" to the query
    if search_query:
        from sqlalchemy import or_
        query = query.filter(
            or_(
                employees.name.ilike(f"%{search_query}%"),
                employees.emp_id.ilike(f"%{search_query}%")
            )
        )

    # 4. EXECUTE the query (This gets the search results OR the full list)
    all_employees = query.all()

    return render_template('index.html', employees=all_employees)

#add employees
@app.route('/add', methods=['POST'])
def add_employee():

    if current_user.role.name != 'admin':
        flash("Unauthorized! Only admins can add new employees.")
        return redirect(url_for('index'))
    
    # 1. Get data from the form (using the 'name' labels from HTML)
    # We use a default '0' for salary if it's left empty
    n = request.form.get('name').strip().title()
    e = request.form.get('email')
    birth_date = request.form.get('dob')
    d = request.form.get('department')
    s = request.form.get('salary') or 0
    doj = request.form.get('date_joined')
    g = request.form.get('gender')
    
    # logic for server default current date for doj
    if  doj == "":
        doj = None

    #  Create the Python object
    new_emp = employees(name=n, email=e, dob= birth_date,  department=d, salary=s, date_joined = doj, gender=g)

    #  The Database Handshake
    db.session.add(new_emp)
    db.session.commit()

    # Success! Now go back to the home page to see the new row
    return redirect(url_for('index'))

#edit employees
@app.route('/edit/<int:emp_id>', methods=['GET', 'POST'])
def edit_employee(emp_id):
    # 1. Fetch the specific employee from MySQL
    emp = employees.query.get_or_404(emp_id)

    if request.method == 'POST':
        # 2. Update the object with new form data
        emp.name = request.form.get('name').strip().title()
        emp.email = request.form.get('email')
        emp.department = request.form.get('department')
        emp.dob = request.form.get('dob')
        emp.salary = request.form.get('salary')
        emp.gender = request.form.get('gender').strip().title()
        
        # Handle the date (the None logic we discussed!)
        date_val = request.form.get('date_joined')
        emp.date_joined = date_val if date_val else None
        
        # 3. Save changes
        db.session.commit()
        flash(f"Success! {emp.name}'s profile has been updated.", "success")
        return redirect('/')

    # 4. If just clicking "Edit", show the page with the employee data
    return render_template('edit.html', employee=emp)

#delete employees
@app.route('/delete/<int:id>')
def delete_employee(id):
    # This 'id' comes from the URL
    target = employees.query.get(id)
    
    if target:
        db.session.delete(target)
        db.session.commit()
        print(f"DEBUG: Employee {id} deleted successfully.")
    
    return redirect(url_for('index'))

#attendance block

@app.route('/attendance/present/<int:emp_id>', methods=['POST'])
@login_required
def mark_present(emp_id):
    # 1. Security Check: Only admins can mark attendance
    if current_user.role.name != 'admin':
        flash("Unauthorized! Only admins can mark attendance.")
        return redirect(url_for('index'))

    # 2. IP Security Check (The "Simple" version we discussed)
    # On Localhost, this will be 127.0.0.1. On Render, use the header check.
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    # For now, let's just print it to your terminal so you can see it working
    print(f"DEBUG: Attendance request from IP: {user_ip}")

    # 3. Check if attendance for TODAY already exists
    today = date.today()
    existing = attendance.query.filter_by(emp_id=emp_id, work_date=today).first()

    if existing:
        flash(f"Attendance already marked for today!")
    else:
        # 4. Create the record (using the table name 'attendance' from your models)
        new_rec = attendance(
            emp_id=emp_id, 
            work_date=today, 
            status='Present' # This matches your ENUM
        )
        db.session.add(new_rec)
        db.session.commit()
        flash("Success! Attendance marked.")

    return redirect(url_for('index'))

#----------------------------------------------attendance log--------------------------

# --- View Attendance History ---
@app.route('/attendance/history/<int:emp_id>')
@login_required
def view_attendance(emp_id):
    # 1. Fetch the employee
    emp = employees.query.get_or_404(emp_id)
    
    # 2. SECURITY CHECK
    # Admin can see anyone. User can ONLY see themselves.
    if current_user.role.name != 'admin' and current_user.emp_id != emp_id:
        flash("Unauthorized! You can only view your own history.")
        return redirect(url_for('index'))

    # 3. Fetch logs for this specific ID
    logs = attendance.query.filter_by(emp_id=emp_id).order_by(attendance.work_date.desc()).all()

    # Logic for Statistics
    present = attendance.query.filter_by(emp_id=emp_id, status='Present').count()
    leave = attendance.query.filter_by(emp_id=emp_id, status='Leave').count()
    total = present + leave # Total days recorded

    percentage = 0
    if total > 0:
        percentage = round((present / total) * 100, 2)

    return render_template('history.html', 
                           employee=emp, 
                           logs=logs, 
                           present=present, 
                           leaves=leave, 
                           total=total,
                           percentage = percentage,
                           )
    
    # 4. Send to the SAME history page
    return render_template('history.html', employee=emp, logs=logs)

#-------------leave---------------------------------

@app.route('/attendance/leave/<int:emp_id>', methods=['POST'])
@login_required
def mark_leave(emp_id):
    if current_user.role.name != 'admin':
        flash("Unauthorized!")
        return redirect(url_for('index'))
    
    # Check if a record (Present or Leave) already exists for today
    from datetime import date
    existing = attendance.query.filter_by(emp_id=emp_id, work_date=date.today()).first()
    
    if existing:
        flash(f"Status already marked as {existing.status} for today!")
    else:
        new_leave = attendance(emp_id=emp_id, work_date=date.today(), status='Leave')
        db.session.add(new_leave)
        db.session.commit()
        flash("Leave marked successfully.")
    return redirect(url_for('index'))


#-------------attendance delete only by admin-------------------

@app.route('/attendance/delete/<int:attendance_id>')
@login_required
def delete_attendance(attendance_id):
    # 1. only admin should be allowed to delete logs
    if current_user.role.name != 'admin':
        flash("Unauthorized! Only admins can remove attendance logs.")
        return redirect(url_for('index'))

    # 2. finding record in the attendance table
    record = attendance.query.get_or_404(attendance_id)
    emp_id = record.emp_id # Keep the emp_id so we can redirect back to the same history page
    
    # 3. Delete it
    db.session.delete(record)
    db.session.commit()
    
    flash("Attendance record removed successfully.")
    return redirect(url_for('view_attendance', emp_id=emp_id))


if __name__ == '__main__':
       app.run(debug=True)


    