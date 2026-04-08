# Placement-Portal-Application-V1
This is the MAD1 project of IIT Madras BS Data Science


# PlaceHub - Campus Placement Management System

**PlaceHub** is a centralized, role-based web application designed to streamline the campus recruitment lifecycle. It connects Institute Administrators, Recruiting Companies, and Students into a single, secure ecosystem, replacing manual spreadsheet tracking with automated, intelligent workflows.

## Key Features & Highlights

### Advanced System Security & Logic
* **Intelligent Eligibility Engine:** The backend actively filters placement drives, hiding them from students who do not meet the strict Minimum CGPA or Passing Year criteria set by companies.
* **Bi-Directional Blacklisting:** If an admin blacklists a company, their drives instantly vanish from student dashboards. If a student is blacklisted, companies can no longer see their applications.
* **Live Search Filtering:** Real-time, vanilla JavaScript search bars implemented across Admin, Company, and Student dashboards for instant table and card filtering.
* **Robust Password Security:** Features a dynamic frontend password strength meter paired with strict backend regex validation (requiring uppercase, lowercase, numbers, and symbols).
* **Age Verification:** Backend date-math calculation ensures students are legally 18+ based on their exact birthdate before allowing registration.

### Admin (Institute) Role
* Pre-existing superuser access with a global statistical dashboard.
* Approve or reject pending Company registrations and newly created Placement Drives.
* View, manage, and blacklist Students and Companies.
* Track all historical application data across the institute.

### Company Role
* Secure registration (requires Admin approval to access the dashboard).
* Create and manage Placement Drives (Job Postings).
* Set strict eligibility criteria (CGPA, Passing Year, Location, Salary).
* View student applications, download PDF resumes natively, and update selection statuses (Applied -> Shortlisted/Selected/Rejected).

### Student Role
* Self-registration and comprehensive profile management.
* Upload Profile Photos and PDF Resumes.
* Browse approved and eligible placement drives.
* One-click application system (backend prevents duplicate applications).
* Track real-time application status and placement history.

---

## Technology Stack
* **Backend Framework:** Python, Flask
* **Database:** SQLite, Flask-SQLAlchemy (ORM)
* **Frontend:** HTML5, Custom CSS (CSS Variables, Flexbox/Grid), Jinja2 Templating
* **Interactivity:** Vanilla JavaScript (Modals, Password Meter, Live Search)
* **Security:** Werkzeug (`generate_password_hash`, `check_password_hash`)

---

## Installation & Setup

Follow these steps to run the application on your local machine.

### 1. Prerequisites
Ensure you have Python 3.8+ installed on your system.

### 2. Clone the Repository
```bash
git clone https://github.com/yourusername/placehub.git
cd placehub
```

### 3. Create a Virtual Environment (Recommended)
```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install Flask Flask-SQLAlchemy Werkzeug
```
*(Or `pip install -r requirements.txt` if you generated one).*

### 5. Initialize the Database & Run the App
The application is configured to programmatically generate the `placement.db` database file on its first run using `db.create_all()`.
```bash
python app.py
```

The application will be running at `http://127.0.0.1:5000/`.

---

## Default Credentials

To test the application, you can register new Student and Company accounts. However, the **Admin** account is a pre-existing superuser. 

Use the following credentials to access the Admin Dashboard:
* **Email:** `admin@placementhub.com`
* **Password:** `admin@12345`

---

## Folder Structure

```text
placehub/
│
├── app.py                  # Main Flask application, routing, and business logic
├── models.py               # SQLAlchemy Database Schemas and Relationships
│
├── static/                 # Static assets (images, PDFs, CSS)
│   ├── photos/             # Uploaded student profile pictures
│   ├── logos/              # Uploaded company logos
│   └── resumes/            # Uploaded student PDF resumes
│
└── templates/              # Jinja2 HTML Templates
    ├── home.html, login.html
    ├── studentregister.html, companyregister.html
    ├── admin_dashboard.html, admin_students.html, admin_drives.html, admin_companies.html
    ├── company_dashboard.html, company_drives.html, company_applications.html
    └── student_dashboard.html, student_drives.html, student_applications.html
```

---

## Database Architecture

The database consists of 4 primary relational tables:
1. **Student:** Stores academic details, personal info, and blacklist status.
2. **Company:** Stores HR contact info, corporate details, and approval status.
3. **Drive:** Linked to a Company (`company_id`). Stores job details, salary, deadlines, and eligibility minimums.
4. **Application:** The junction table tracking which Student (`student_id`) applied to which Drive (`drive_id`), along with the current recruitment status.
