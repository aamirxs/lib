import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
import calendar
from dateutil.relativedelta import relativedelta
from report_generator import generate_student_report, generate_monthly_report

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# Handle PostgreSQL URL from Render
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///fee_management.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Models
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    seat_number = db.Column(db.String(20), unique=True, nullable=False)
    phone_number = db.Column(db.String(15))
    joining_date = db.Column(db.Date, nullable=False)
    monthly_fee = db.Column(db.Float, nullable=False)
    fees = db.relationship('Fee', backref='student', lazy=True)

class Fee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    month = db.Column(db.Date, nullable=False)
    paid = db.Column(db.Boolean, default=False)
    payment_date = db.Column(db.Date)

def init_db():
    with app.app_context():
        db.create_all()
        
# Initialize database tables
init_db()

def generate_fees_for_all_students():
    try:
        students = Student.query.all()
        current_date = datetime.now().date()
        current_month = date(current_date.year, current_date.month, 1)
        
        for student in students:
            # Check if fee for current month exists
            existing_fee = Fee.query.filter_by(
                student_id=student.id,
                month=current_month
            ).first()
            
            if not existing_fee:
                new_fee = Fee(
                    student_id=student.id,
                    amount=student.monthly_fee,
                    month=current_month,
                    paid=False
                )
                db.session.add(new_fee)
        
        db.session.commit()
    except Exception as e:
        print(f"Error generating fees: {str(e)}")
        db.session.rollback()

# Routes
@app.route('/')
def dashboard():
    # Generate fees for current month if not already generated
    generate_fees_for_all_students()
    
    students = Student.query.all()
    unpaid_fees = Fee.query.filter_by(paid=False).all()
    monthly_collection = sum(fee.amount for fee in Fee.query.filter(
        Fee.paid == True,
        Fee.payment_date >= datetime.now().date().replace(day=1)
    ).all())
    return render_template('dashboard.html', students=students, unpaid_fees=unpaid_fees, monthly_collection=monthly_collection)

@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        try:
            joining_date_str = request.form.get('joining_date')
            if not joining_date_str:
                flash('Joining date is required', 'error')
                return redirect(url_for('add_student'))

            student = Student(
                name=request.form.get('name'),
                seat_number=request.form.get('seat_number'),
                phone_number=request.form.get('phone_number'),
                joining_date=datetime.strptime(joining_date_str, '%Y-%m-%d').date(),
                monthly_fee=float(request.form.get('monthly_fee', 1000.0))
            )
            db.session.add(student)
            db.session.commit()
            
            # Generate fee for current month for new student
            generate_fees_for_all_students()
            flash('Student added successfully', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding student: {str(e)}', 'error')
            return redirect(url_for('add_student'))
    
    return render_template('add_student.html')

@app.route('/edit_student/<int:student_id>', methods=['GET', 'POST'])
def edit_student(student_id):
    student = Student.query.get_or_404(student_id)
    if request.method == 'POST':
        student.name = request.form.get('name')
        student.seat_number = request.form.get('seat_number')
        student.phone_number = request.form.get('phone_number')
        student.joining_date = datetime.strptime(request.form.get('joining_date'), '%Y-%m-%d').date()
        student.monthly_fee = float(request.form.get('monthly_fee', student.monthly_fee))
        try:
            db.session.commit()
            flash('Student updated successfully')
            return redirect(url_for('dashboard'))
        except:
            db.session.rollback()
            flash('Error updating student. Seat number might be already taken.')
    return render_template('edit_student.html', student=student)

@app.route('/delete_student/<int:student_id>', methods=['POST'])
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    try:
        db.session.delete(student)
        db.session.commit()
        flash('Student deleted successfully')
    except:
        db.session.rollback()
        flash('Error deleting student')
    return redirect(url_for('dashboard'))

@app.route('/add_fee/<int:student_id>', methods=['GET', 'POST'])
def add_fee(student_id):
    student = Student.query.get_or_404(student_id)
    if request.method == 'POST':
        month = datetime.strptime(request.form.get('month'), '%Y-%m').date()
        # Check if fee record already exists for this month
        existing_fee = Fee.query.filter(
            Fee.student_id == student_id,
            Fee.month == month
        ).first()
        
        if existing_fee:
            existing_fee.amount = float(request.form.get('amount'))
            existing_fee.paid = request.form.get('paid') == 'True'
            existing_fee.payment_date = datetime.strptime(request.form.get('payment_date'), '%Y-%m-%d').date() if request.form.get('payment_date') else None
        else:
            fee = Fee(
                student_id=student_id,
                amount=float(request.form.get('amount')),
                month=month,
                paid=request.form.get('paid') == 'True',
                payment_date=datetime.strptime(request.form.get('payment_date'), '%Y-%m-%d').date() if request.form.get('payment_date') else None
            )
            db.session.add(fee)
        
        try:
            db.session.commit()
            flash('Fee record updated successfully')
        except:
            db.session.rollback()
            flash('Error updating fee record')
        
        return redirect(url_for('student_details', student_id=student_id))
    
    return render_template('add_fee.html', student=student)

@app.route('/student/<int:student_id>')
def student_details(student_id):
    student = Student.query.get_or_404(student_id)
    return render_template('student_details.html', student=student)

@app.route('/unpaid_fees')
def unpaid_fees():
    # Generate fees for current month if not already generated
    generate_fees_for_all_students()
    
    # Get all students with unpaid fees
    unpaid = Fee.query.filter_by(paid=False).join(Student).order_by(Fee.month.desc()).all()
    return render_template('unpaid_fees.html', unpaid_fees=unpaid)

@app.route('/generate_student_report/<int:student_id>')
def generate_student_report_route(student_id):
    student = Student.query.get_or_404(student_id)
    filename = f'reports/student_{student.seat_number}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    
    # Create reports directory if it doesn't exist
    os.makedirs('reports', exist_ok=True)
    
    # Generate the report
    generate_student_report(student, student.fees, filename)
    
    # Send the file to the user
    return send_file(filename, as_attachment=True)

@app.route('/generate_monthly_report', methods=['GET', 'POST'])
def generate_monthly_report_route():
    if request.method == 'POST':
        month = datetime.strptime(request.form.get('month'), '%Y-%m').date()
        filename = f'reports/monthly_report_{month.strftime("%Y%m")}.pdf'
        
        # Create reports directory if it doesn't exist
        os.makedirs('reports', exist_ok=True)
        
        # Get all students
        students = Student.query.order_by(Student.seat_number).all()
        
        # Generate the report
        generate_monthly_report(students, month, filename)
        
        # Send the file to the user
        return send_file(filename, as_attachment=True)
    
    return render_template('generate_monthly_report.html')

if __name__ == '__main__':
    app.run(debug=True)
