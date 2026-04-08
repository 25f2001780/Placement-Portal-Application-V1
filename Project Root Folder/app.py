from flask import Flask, render_template, request, session, redirect, url_for, flash
from models import db, Student, Company, Drive, Application
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime,date
import time
import os
import re

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///placement.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/resumes'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
app.config['LOGO_FOLDER'] = 'static/logos'
os.makedirs(app.config['LOGO_FOLDER'], exist_ok=True)
app.config['PHOTO_FOLDER'] = 'static/photos'
os.makedirs('static/photos', exist_ok=True)
# REQUIRED: Set a secret key for session management and flash messages
app.secret_key = os.urandom(24) 

db.init_app(app)
with app.app_context():
    db.create_all()
    print("Database ready!")

def is_strong_password(password):
    """
    Checks if password is >= 8 chars and contains at least:
    1 uppercase, 1 lowercase, 1 number, and 1 special character.
    """
    if len(password) < 8: return False
    if not re.search(r"[A-Z]", password): return False
    if not re.search(r"[a-z]", password): return False
    if not re.search(r"\d", password): return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password): return False
    return True

# ==========================================
# CUSTOM ERROR HANDLERS
# ==========================================
@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', code="404", title="Page Not Found", message="The page you are looking for doesn't exist or has been moved."), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', code="500", title="Internal Server Error", message="Something went wrong on our end. Please try again later."), 500


# ==========================================
# GLOBAL AUTO-MAINTENANCE LOGIC
# ==========================================
def check_expired_drives():
    """Checks for drives that have passed their deadline, closes them, and auto-rejects unresponded applicants."""
    now = datetime.utcnow()
    expired_drives = Drive.query.filter(Drive.deadline < now, Drive.status == 'active').all()
    
    for drive in expired_drives:
        drive.status = 'closed'
        # If the drive closed, anyone still 'applied' is automatically rejected
        for app in drive.applications:
            if app.status.lower() == 'applied':
                app.status = 'rejected'
                
    if expired_drives:
        db.session.commit()


# ==========================================
# AUTHENTICATION ROUTES
# ==========================================
@app.route('/', methods=["GET"])
def home():
    return render_template('home.html')

@app.route('/students')
def list_students():
    all_students = Student.query.all()
    return render_template('students.html', students=all_students)

@app.route('/signupStudent', methods=["GET"])
def signup():
    return render_template("studentregister.html")

@app.route('/signupCompany', methods=["GET"])
def signupC():
    return render_template("companyregister.html")

@app.route('/registerStudent', methods=["POST"])
def register():
    firstname = request.form.get("firstname")
    lastname = request.form.get("lastname")
    email = request.form.get("email")
    
    raw_password = request.form.get("password")
    if not raw_password or not is_strong_password(raw_password):
        return render_template("studentregister.html", error="Password must be at least 8 characters long and include an uppercase letter, a lowercase letter, a number, and a special character.")
    password = generate_password_hash(raw_password)
    
    phonenumber = request.form.get("phone")
    depart = request.form.get("department")
    Cgpa = request.form.get("cgpa")
    pyear = request.form.get("passingYear")
    
    bdate_str = request.form.get("birthday")
    bdate_obj = None
    if not bdate_str:
        return render_template("studentregister.html", error="Birthdate is required.")
        
    bdate_obj = datetime.strptime(bdate_str, '%Y-%m-%d').date()
    today = date.today()
    
    # Calculate exact age considering leap years and months
    age = today.year - bdate_obj.year - ((today.month, today.day) < (bdate_obj.month, bdate_obj.day))
    
    if age < 18:
        # Reject registration if under 18
        return render_template("studentregister.html", error="Registration failed: You must be at least 18 years old to register.")

    existing_student = Student.query.filter_by(email=email).first()
    existing_company = Company.query.filter_by(company_email=email).first()

    if not existing_student and not existing_company:
        student_data = Student(
            fname=firstname,
            lname=lastname,
            email=email,
            password=password,
            phone=phonenumber,
            department=depart,
            cgpa=Cgpa,
            passing_year=pyear,
            bdate=bdate_obj,
            is_blacklisted=False  # Changed from status='active'
        )
        db.session.add(student_data)
        db.session.commit()
        flash("Registration successful! Please login.", "success")
        return redirect(url_for('login'))
    else:
        return "An account with this email already exists."

@app.route('/registerCompany', methods=["POST"])
def registerC():
    email = request.form.get("email")
    raw_password = request.form.get("password")
    company_name = request.form.get("companyname")
    hrnumber = request.form.get("phone")
    hrname = request.form.get("hrname")
    sitename = request.form.get("site")

    if not raw_password or not is_strong_password(raw_password):
        return render_template("companyregister.html", error="Password must be at least 8 characters long and include an uppercase letter, a lowercase letter, a number, and a special character.")

    if not all([email, raw_password, company_name, hrnumber, hrname]):
        flash("Please fill out all required fields.", "error")
        return render_template("companyregister.html",error="Please Fill all fields") 

    existing_student = Student.query.filter_by(email=email).first()
    existing_company = Company.query.filter_by(company_email=email).first()

    if existing_student or existing_company:
        return render_template("companyregister.html",error="Email already Exists.")

    password = generate_password_hash(raw_password)
    
    try:
        company_data = Company(
            company_email=email,
            password=password,
            company_name=company_name,
            hr_phone=hrnumber,
            hr_name=hrname,
            company_site=sitename,
            status='pending' 
        )
        db.session.add(company_data)
        db.session.commit()
        
        session['company_email'] = email
        session['company_name'] = company_name
        return render_template("pending.html")
        
    except Exception as e:
        db.session.rollback()
        flash("An unexpected error occurred. Please try again later.", "error")
        return redirect(url_for('signupC'))

@app.route('/login', methods=["GET"])
def login():
    return render_template("login.html")

@app.route('/check', methods=["POST"])
def check():
    email = request.form.get("email")
    password = request.form.get("password")
    
    existing_company = Company.query.filter_by(company_email=email).first()
    existing_student = Student.query.filter_by(email=email).first()

    # 1. Check Student
    if existing_student and check_password_hash(existing_student.password, password):
        if getattr(existing_student, 'is_blacklisted', False):
            return render_template('blacklisted.html')
        session['user_email'] = existing_student.email
        return redirect(url_for('student_dashboard'))

    # 2. Check Company
    elif existing_company and check_password_hash(existing_company.password, password):
        if existing_company.status == 'pending':
            session['company_email'] = existing_company.company_email
            session['company_name'] = existing_company.company_name
            return render_template("pending.html")
        elif existing_company.status == 'approved':
            session['company_email'] = existing_company.company_email
            return redirect(url_for('company_dashboard'))
        elif existing_company.status == 'blacklisted':
            return render_template("blacklisted.html")
            
    # 3. Check Admin
    elif email == "admin@placementhub.com" and password == "admin@12345":
        session['admin_email'] = email
        session['admin'] = True
        return redirect(url_for('admin_dashboard'))
        
    else:
        return render_template("login.html", error="Invalid password or Email")

@app.route('/logout')
def logout():
    session.pop('user_email', None)
    session.pop('company_email', None)
    session.pop('admin_email', None)
    flash("You have been successfully logged out.", "success")
    return redirect(url_for('login'))


# ==========================================
# STUDENT LOGIC & ROUTES
# ==========================================
def get_student_context():
    student = Student.query.filter_by(email=session['user_email']).first()
    
    photo_filename = f"{student.student_id}.jpg"
    photo_path = os.path.join(app.config['PHOTO_FOLDER'], photo_filename)
    has_photo = os.path.exists(photo_path)
    photo_url = url_for('static', filename=f'photos/{photo_filename}') + f"?t={int(time.time())}" if has_photo else ""
    has_resume = os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], f"{student.student_id}.pdf"))

    # LOGIC CHANGE: Only pull applications where the company is NOT blacklisted
    valid_apps = [app for app in student.applications if getattr(app.drive.company, 'status', '') != 'blacklisted']

    total_apps = len(valid_apps)
    shortlisted_apps = sum(1 for app in valid_apps if app.status == 'shortlisted')
    
    formatted_history = []
    sorted_apps = sorted(valid_apps, key=lambda x: x.applied_on, reverse=True) if valid_apps else []
    for app_record in sorted_apps:
        formatted_history.append({
            'drive_title': app_record.drive.job_title, 
            'company_name': app_record.drive.company.company_name, 
            'location': getattr(app_record.drive.company, 'location', 'Not Specified'),
            'applied_on': app_record.applied_on.strftime("%b %d, %Y") if app_record.applied_on else "N/A",
            'status': app_record.status.upper()
        })

    formatted_drives = []
    active_drives_raw = Drive.query.filter_by(status='active').all()
    for drive in active_drives_raw:
        # Hide drives if the company is blacklisted
        if drive.company.status == 'blacklisted':
            continue
            
        # Must meet both passing year and Min CGPA requirement
        if student.passing_year <= drive.pass_year and student.cgpa >= drive.min_cgpa:
            app_count = len(drive.applications)
            has_applied = any(app.student_id == student.student_id for app in drive.applications)
            formatted_drives.append({
                'drive_id': drive.drive_id,
                'company_id': drive.company_id,
                'job_title': drive.job_title,
                'company_name': drive.company.company_name,
                'salary_str': f"₹{drive.salary:g} LPA" if drive.salary else "Not Disclosed",
                'deadline_str': drive.deadline.strftime("%b %d, %Y") if drive.deadline else "N/A",
                'min_cgpa': drive.min_cgpa,
                'pass_year': drive.pass_year,
                'description': drive.description,
                'location': getattr(drive.company, 'location', 'Not Specified'),
                'applicants_count': app_count,
                'applied': has_applied
            })
            
    return {
        'StudentName': f"{student.fname} {student.lname}", 'student': student, 'total_applications_count': total_apps,
        'shortlisted_applications_count': shortlisted_apps, 'application_history': formatted_history, 'has_resume': has_resume,
        'drives': formatted_drives, 'has_photo': has_photo, 'photo_url': photo_url
    }

def check_student_security():
    if 'user_email' not in session: return url_for('login')
    student = Student.query.filter_by(email=session['user_email']).first()
    if not student: return url_for('login')
    
    # Use boolean check here
    if getattr(student, 'is_blacklisted', False):
        return 'blacklisted'
    return None

@app.route('/student_dashboard', methods=["GET"])
def student_dashboard():
    sec = check_student_security()
    if sec == 'blacklisted': return render_template("blacklisted.html")
    elif sec: return redirect(sec)
    check_expired_drives()
    return render_template("student_dashboard.html", **get_student_context())

@app.route('/student_drives', methods=["GET"])
def student_drives():
    sec = check_student_security()
    if sec == 'blacklisted': return render_template("blacklisted.html")
    elif sec: return redirect(sec)
    check_expired_drives()
    return render_template("student_drives.html", **get_student_context())

@app.route('/student_applications', methods=["GET"])
def student_applications():
    sec = check_student_security()
    if sec == 'blacklisted': return render_template("blacklisted.html")
    elif sec: return redirect(sec)
    check_expired_drives()
    return render_template("student_applications.html", **get_student_context())

@app.route('/student_settings', methods=["GET"])
def student_settings():
    sec = check_student_security()
    if sec == 'blacklisted': return render_template("blacklisted.html")
    elif sec: return redirect(sec)
    return render_template("student_settings.html", **get_student_context())

@app.route('/uploadStudentPhoto', methods=['POST'])
def upload_student_photo():
    if 'user_email' not in session: return redirect(url_for('login'))
    student = Student.query.filter_by(email=session['user_email']).first()
    if student and 'photo' in request.files:
        file = request.files['photo']
        if file and file.filename.lower().endswith(('.jpg', '.jpeg')):
            file.save(os.path.join(app.config['PHOTO_FOLDER'], f"{student.student_id}.jpg"))
    return redirect(request.referrer or url_for('student_settings'))

@app.route('/uploadResume', methods=['POST'])
def upload_resume():
    if 'user_email' not in session: return redirect(url_for('login'))
    student = Student.query.filter_by(email=session['user_email']).first()
    if student:
        if 'resume' not in request.files or request.files['resume'].filename == '':
            flash('No file selected', 'error')
            return redirect(request.referrer or url_for('student_dashboard'))
        file = request.files['resume']
        if file and file.filename.lower().endswith('.pdf'):
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], f"{student.student_id}.pdf"))
            flash("Resume uploaded successfully!", "success")
    return redirect(request.referrer or url_for('student_dashboard'))

@app.route('/updateProfile', methods=['POST'])
def update_profile():
    if 'user_email' not in session: return redirect(url_for('login'))
    student = Student.query.filter_by(email=session['user_email']).first()
    if student:
        student.fname = request.form.get('firstname', student.fname)
        student.lname = request.form.get('lastname', student.lname)
        student.phone = request.form.get('phone', student.phone)
        student.cgpa = float(request.form.get('cgpa')) if request.form.get('cgpa') else student.cgpa
        student.department = request.form.get('department', student.department)
        student.passing_year = int(request.form.get('passing_year')) if request.form.get('passing_year') else student.passing_year
        db.session.commit()
    return redirect(request.referrer or url_for('student_settings'))

@app.route('/changePassword', methods=['POST'])
def change_password():
    if 'user_email' not in session: return redirect(url_for('login'))
    student = Student.query.filter_by(email=session['user_email']).first()
    if student:
        if check_password_hash(student.password, request.form.get('current_password')):
            if request.form.get('new_password') == request.form.get('confirm_password'):
                student.password = generate_password_hash(request.form.get('new_password'))
                db.session.commit()
                flash("Password updated successfully.", "success")
            else:
                flash("New passwords do not match.", "error")
        else:
            flash("Incorrect current password.", "error")
    return redirect(request.referrer or url_for('student_settings'))

@app.route('/apply_drive/<int:drive_id>', methods=['POST'])
def apply_drive(drive_id):
    if 'user_email' not in session: return redirect(url_for('login'))
    student = Student.query.filter_by(email=session['user_email']).first()
    if not student: return redirect(url_for('login'))
    
    existing_app = Application.query.filter_by(student_id=student.student_id, drive_id=drive_id).first()
    if not existing_app:
        new_app = Application(student_id=student.student_id, drive_id=drive_id, status='applied')
        db.session.add(new_app)
        db.session.commit()
    return redirect(request.referrer or url_for('student_dashboard'))


# ==========================================
# COMPANY LOGIC & ROUTES
# ==========================================
def get_company_context():
    company = Company.query.filter_by(company_email=session['company_email']).first()
    drives = Drive.query.filter_by(company_id=company.company_id).order_by(Drive.drive_id.desc()).all()
    
    total_drives = len(drives)
    active_drives = sum(1 for d in drives if d.status.lower() in ['active', 'approved'])
    total_applicants = 0
    formatted_drives = []
    
    for d in drives:
        apps = d.applications if d.applications else []
        
        # LOGIC CHANGE: Only count and show applications from NON-blacklisted students
        valid_apps = [a for a in apps if a.student and not getattr(a.student, 'is_blacklisted', False)]
        
        total_applicants += len(valid_apps)
        drive_apps = []
        for a in valid_apps:
            drive_apps.append({
                'app_id': a.application_id, 'student_id': a.student.student_id, 'name': f"{a.student.fname} {a.student.lname}",
                'email': a.student.email, 'phone': a.student.phone, 'department': a.student.department, 'cgpa': a.student.cgpa,
                'status': a.status.upper() if a.status else 'APPLIED', 'applied_on': a.applied_on.strftime("%b %d, %Y") if a.applied_on else "N/A"
            })
            
        formatted_drives.append({
            'drive_id': d.drive_id, 'job_title': d.job_title or 'Untitled', 'deadline_raw': d.deadline.strftime("%Y-%m-%d") if d.deadline else "",
            'deadline_str': d.deadline.strftime("%b %d, %Y") if d.deadline else "N/A", 'applicants_count': len(valid_apps),
            'status': d.status.upper() if d.status else 'ACTIVE', 'salary': d.salary or 0.0, 'min_cgpa': d.min_cgpa or 0.0,
            'pass_year': d.pass_year or 2026, 'description': d.description or '', 'location': getattr(company, 'location', 'Not Specified'), 
            'applicants': drive_apps
        })

    all_apps_query = Application.query.filter(Application.drive_id.in_([d.drive_id for d in drives])).order_by(Application.applied_on.desc()).all()
    all_applicants = []
    for a in all_apps_query:
        # LOGIC CHANGE: Exclude blacklisted students from recent applicants list
        if a.student and a.drive and not getattr(a.student, 'is_blacklisted', False):
            all_applicants.append({
                'app_id': a.application_id, 'student_id': a.student.student_id, 'name': f"{a.student.fname} {a.student.lname}",
                'job_title': a.drive.job_title, 'department': a.student.department, 'status': a.status.upper() if a.status else 'APPLIED',
                'email': a.student.email, 'phone': a.student.phone, 'cgpa': a.student.cgpa, 'applied_on': a.applied_on.strftime("%b %d, %Y") if a.applied_on else "N/A"
            })
            
    logo_filename = f"{company.company_id}.jpg"
    has_logo = os.path.exists(os.path.join(app.config.get('LOGO_FOLDER', 'static/logos'), logo_filename))
    logo_url = url_for('static', filename=f'logos/{logo_filename}') + f"?t={int(time.time())}" if has_logo else ""

    return {
        'company': company, 'total_drives': total_drives, 'active_drives': active_drives, 'total_applicants': total_applicants,
        'drives': formatted_drives, 'all_applicants': all_applicants, 'recent_applicants': all_applicants[:5], 'has_logo': has_logo, 'logo_url': logo_url
    }

def check_company_security():
    if 'company_email' not in session: return url_for('login')
    company = Company.query.filter_by(company_email=session['company_email']).first()
    if not company: return url_for('login')
    if company.status == 'pending': return 'pending'
    if company.status == 'blacklisted': return 'blacklisted'
    return None

@app.route('/company_dashboard', methods=["GET"])
def company_dashboard():
    sec = check_company_security()
    if sec == 'pending': return render_template("pending.html")
    elif sec == 'blacklisted': return render_template("blacklisted.html")
    elif sec: return redirect(sec)
    check_expired_drives()
    return render_template("company_dashboard.html", **get_company_context())

@app.route('/company_drives', methods=["GET"])
def company_drives():
    sec = check_company_security()
    if sec == 'pending': return render_template("pending.html")
    elif sec == 'blacklisted': return render_template("blacklisted.html")
    elif sec: return redirect(sec)
    check_expired_drives()
    return render_template("company_drives.html", **get_company_context())

@app.route('/company_applications', methods=["GET"])
def company_applications():
    sec = check_company_security()
    if sec == 'pending': return render_template("pending.html")
    elif sec == 'blacklisted': return render_template("blacklisted.html")
    elif sec: return redirect(sec)
    return render_template("company_applications.html", **get_company_context())

@app.route('/company_settings', methods=["GET"])
def company_settings():
    sec = check_company_security()
    if sec == 'pending': return render_template("pending.html")
    elif sec == 'blacklisted': return render_template("blacklisted.html")
    elif sec: return redirect(sec)
    return render_template("company_settings.html", **get_company_context())

@app.route('/updateCompanyProfile', methods=['POST'])
def update_company_profile():
    if 'company_email' not in session: return redirect(url_for('login'))
    company = Company.query.filter_by(company_email=session['company_email']).first()
    if company:
        company.company_name = request.form.get('company_name', company.company_name)
        company.hr_name = request.form.get('hr_name', company.hr_name)
        company.hr_phone = request.form.get('phone', company.hr_phone)
        company.company_site = request.form.get('website', company.company_site)
        
        # ADD THIS LINE: Save the location
        company.location = request.form.get('location', company.location)
        
        db.session.commit()
    return redirect(request.referrer or url_for('company_dashboard'))

@app.route('/changeCompanyPassword', methods=['POST'])
def change_company_password():
    if 'company_email' not in session: return redirect(url_for('login'))
    company = Company.query.filter_by(company_email=session['company_email']).first()
    if company:
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        if check_password_hash(company.password, current_password):
            if new_password == confirm_password:
                company.password = generate_password_hash(new_password)
                db.session.commit()
                flash("Password updated successfully.", "success")
            else:
                flash("New passwords do not match.", "error")
        else:
            flash("Incorrect current password.", "error")
    return redirect(request.referrer or url_for('company_settings'))

@app.route('/uploadCompanyLogo', methods=['POST'])
def upload_company_logo():
    if 'company_email' not in session: return redirect(url_for('login'))
    company = Company.query.filter_by(company_email=session['company_email']).first()
    if company and 'logo' in request.files:
        file = request.files['logo']
        if file and file.filename.lower().endswith(('.jpg', '.jpeg')):
            file.save(os.path.join(app.config.get('LOGO_FOLDER', 'static/logos'), f"{company.company_id}.jpg"))
    return redirect(request.referrer or url_for('company_dashboard'))

@app.route('/createDrive', methods=['POST'])
def create_drive():
    if 'company_email' not in session: return redirect(url_for('login'))
    company = Company.query.filter_by(company_email=session['company_email']).first()
    
    if company:
        try:
            # 1. Safely parse the date
            deadline_str = request.form.get('deadline')
            deadline = datetime.strptime(deadline_str, "%Y-%m-%d") if deadline_str else datetime.utcnow()
            
            # 2. Safely parse numbers (prevents ValueError crashes)
            s_val = request.form.get('salary')
            salary_val = float(s_val) if s_val and s_val.strip() else 0.0
            
            c_val = request.form.get('min_cgpa')
            cgpa_val = float(c_val) if c_val and c_val.strip() else 0.0
            
            p_val = request.form.get('pass_year')
            pass_year_val = int(p_val) if p_val and p_val.strip() else 2026
            
            # 3. Create the drive
            new_drive = Drive(
                company_id=company.company_id,
                job_title=request.form.get('job_title', 'Untitled'),
                description=request.form.get('description', ''),
                salary=salary_val,
                min_cgpa=cgpa_val,
                pass_year=pass_year_val,
                deadline=deadline,
                status='pending'  # <--- CHANGED THIS FROM 'active'
            )
            
            # 4. Safely handle the location column (prevents DB schema crashes)
            if hasattr(new_drive, 'location'):
                new_drive.location = getattr(company, 'location', 'Not Specified')
                
            db.session.add(new_drive)
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            print(f"CRASH PREVENTED in create_drive: {e}")
            # If you check your terminal when it fails, it will tell you exactly what went wrong!
            
    return redirect(request.referrer or url_for('company_drives'))


@app.route('/editDrive/<int:drive_id>', methods=['POST'])
def edit_drive(drive_id):
    if 'company_email' not in session: return redirect(url_for('login'))
    drive = Drive.query.get(drive_id)
    
    if drive:
        try:
            # 1. Safely parse the date
            deadline_str = request.form.get('deadline')
            if deadline_str: 
                drive.deadline = datetime.strptime(deadline_str, "%Y-%m-%d")
                
            # 2. Safely update numbers
            s_val = request.form.get('salary')
            if s_val and s_val.strip(): drive.salary = float(s_val)
            
            c_val = request.form.get('min_cgpa')
            if c_val and c_val.strip(): drive.min_cgpa = float(c_val)
            
            p_val = request.form.get('pass_year')
            if p_val and p_val.strip(): drive.pass_year = int(p_val)
            
            # 3. Update strings
            drive.job_title = request.form.get('job_title', drive.job_title)
            drive.description = request.form.get('description', drive.description)
            
            # 4. Handle Status and auto-reject logic
            new_status = request.form.get('status', drive.status).lower()
            if new_status == 'closed' and drive.status != 'closed':
                for app in drive.applications:
                    if app.status.lower() == 'applied':
                        app.status = 'rejected'
                        
            drive.status = new_status
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            print(f"CRASH PREVENTED in edit_drive: {e}")
            
    return redirect(request.referrer or url_for('company_drives'))

@app.route('/updateApplicationStatus/<int:app_id>', methods=['POST'])
def update_application_status(app_id):
    if 'company_email' not in session: return redirect(url_for('login'))
    application = Application.query.get(app_id)
    if application:
        new_status = request.form.get('status')
        if new_status in ['applied', 'shortlisted', 'selected', 'rejected']:
            application.status = new_status
            db.session.commit()
    return redirect(request.referrer or url_for('company_applications'))


# ==========================================
# ADMIN LOGIC & ROUTES
# ==========================================
def get_admin_context():
    check_expired_drives() 
    students = Student.query.all()
    companies = Company.query.all()
    drives = Drive.query.all()
    apps = Application.query.all()

    return {
        'students': students, 'companies': companies, 'drives': drives, 'apps': apps,
        'pending_companies': [c for c in companies if c.status == 'pending'],
        'active_drives': [d for d in drives if d.status == 'active'],
        'closed_drives': [d for d in drives if d.status == 'closed'],
        'approved_companies': [c for c in companies if c.status == 'approved'],
        'recent_apps': sorted(apps, key=lambda x: x.applied_on, reverse=True)[:5],
        'placed_students': len([s for s in students if any(a.status.lower() == 'selected' for a in s.applications)])
    }

def check_admin_security():
    if 'admin_email' not in session: return url_for('login')
    return None

@app.route('/admin_dashboard')
def admin_dashboard():
    sec = check_admin_security()
    if sec: return redirect(sec)
    return render_template('admin_dashboard.html', **get_admin_context())

@app.route('/admin_students')
def admin_students():
    sec = check_admin_security()
    if sec: return redirect(sec)
    return render_template('admin_students.html', **get_admin_context())

@app.route('/admin_companies')
def admin_companies():
    sec = check_admin_security()
    if sec: return redirect(sec)
    return render_template('admin_companies.html', **get_admin_context())

@app.route('/admin_drives')
def admin_drives():
    sec = check_admin_security()
    if sec: return redirect(sec)
    return render_template('admin_drives.html', **get_admin_context())

@app.route('/admin_applications')
def admin_applications():
    sec = check_admin_security()
    if sec: return redirect(sec)
    return render_template('admin_applications.html', **get_admin_context())

@app.route('/admin/approve_company/<int:company_id>', methods=['POST'])
def admin_approve_company(company_id):
    # Bulletproof session check
    if 'admin_email' not in session and 'admin' not in session: 
        return redirect(url_for('login'))
        
    company = Company.query.get(company_id)
    if company:
        company.status = 'approved'
        db.session.commit()
        
    return redirect(request.referrer or url_for('admin_dashboard'))

@app.route('/admin/reject_company/<int:company_id>', methods=['POST'])
def admin_reject_company(company_id):
    # Bulletproof session check
    if 'admin_email' not in session and 'admin' not in session: 
        return redirect(url_for('login'))
        
    company = Company.query.get(company_id)
    if company:
        company.status = 'rejected'
        db.session.commit()
        
    return redirect(request.referrer or url_for('admin_dashboard'))

@app.route('/admin/blacklist_company/<int:company_id>', methods=['POST'])
def admin_blacklist_company(company_id):
    if 'admin_email' not in session: return redirect(url_for('login'))
    c = Company.query.get(company_id)
    if c: c.status = 'blacklisted'
    db.session.commit()
    return redirect(request.referrer or url_for('admin_companies'))

@app.route('/admin/unblacklist_company/<int:company_id>', methods=['POST'])
def admin_unblacklist_company(company_id):
    if 'admin_email' not in session: return redirect(url_for('login'))
    c = Company.query.get(company_id)
    if c: c.status = 'approved'
    db.session.commit()
    return redirect(request.referrer or url_for('admin_companies'))

@app.route('/admin/blacklist_student/<int:student_id>', methods=['POST'])
def admin_blacklist_student(student_id):
    if 'admin_email' not in session: return redirect(url_for('login'))
    s = Student.query.get(student_id)
    if s: 
        s.is_blacklisted = True  # Changed to boolean
    db.session.commit()
    return redirect(request.referrer or url_for('admin_students'))

@app.route('/admin/unblacklist_student/<int:student_id>', methods=['POST'])
def admin_unblacklist_student(student_id):
    if 'admin_email' not in session: return redirect(url_for('login'))
    s = Student.query.get(student_id)
    if s: 
        s.is_blacklisted = False # Changed to boolean
    db.session.commit()
    return redirect(request.referrer or url_for('admin_students'))

@app.route('/admin/approve_drive/<int:drive_id>', methods=['POST'])
def admin_approve_drive(drive_id):
    if 'admin' not in session: return redirect(url_for('login'))
    drive = Drive.query.get(drive_id)
    if drive:
        drive.status = 'active'
        db.session.commit()
    return redirect(request.referrer or url_for('admin_drives'))

@app.route('/admin/reject_drive/<int:drive_id>', methods=['POST'])
def admin_reject_drive(drive_id):
    if 'admin' not in session: return redirect(url_for('login'))
    drive = Drive.query.get(drive_id)
    if drive:
        drive.status = 'rejected'
        db.session.commit()
    return redirect(request.referrer or url_for('admin_drives'))

if __name__ == '__main__':
    app.run(debug=True)