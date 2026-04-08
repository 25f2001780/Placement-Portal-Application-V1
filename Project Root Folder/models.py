from flask_sqlalchemy import SQLAlchemy
from flask import Flask
from datetime import datetime

db = SQLAlchemy()

class Student(db.Model):
    __tablename__ = 'student'
    student_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fname = db.Column(db.String(30), nullable=False)
    lname = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False) # Increased length for hashed passwords
    phone = db.Column(db.String(15), nullable=False)    # Changed to String for phone numbers
    department = db.Column(db.String(50), nullable=False)
    cgpa = db.Column(db.Float, nullable=False)
    passing_year = db.Column(db.Integer, nullable=False)
    is_blacklisted = db.Column(db.Boolean, default=False) # Changed to Boolean for efficiency
    bdate=db.Column(db.Date, nullable=False)

    applications = db.relationship('Application', backref='student', lazy=True)

class Company(db.Model):
    __tablename__ = 'company'
    company_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    company_email = db.Column(db.String(120), unique=True, nullable=False)
    company_site=db.Column(db.String(255),unique=True, nullable=True)
    password = db.Column(db.String(255), nullable=False)
    company_name = db.Column(db.String(100), nullable=False)
    hr_phone = db.Column(db.Integer)
    hr_name= db.Column(db.String(60))
    status = db.Column(db.String(20), default='pending')
    location = db.Column(db.String(100), default='Not Specified')

    drives = db.relationship('Drive', backref='company', lazy=True)

class Drive(db.Model):
    __tablename__ = 'drive'
    drive_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.company_id'), nullable=False)
    job_title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    salary = db.Column(db.Float) # Float or standard Integer is safer
    min_cgpa = db.Column(db.Float, nullable=False)
    pass_year = db.Column(db.Integer, nullable=False)
    deadline = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='active')
    applications = db.relationship('Application', backref='drive', lazy=True)

class Application(db.Model):
    __tablename__ = 'application'
    application_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.student_id'), nullable=False)
    drive_id = db.Column(db.Integer, db.ForeignKey('drive.drive_id'), nullable=False)
    status = db.Column(db.String(20), default='applied') # applied, shortlisted, rejected, placed
    applied_on = db.Column(db.DateTime, default=datetime.utcnow)

