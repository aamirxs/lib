from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
from dateutil.relativedelta import relativedelta
from report_generator import generate_student_report, generate_monthly_report

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///data/fee_management.db')

# Ensure the data directory exists
os.makedirs('data', exist_ok=True)

db = SQLAlchemy()
db.init_app(app)

# Models
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    seat_number = db.Column(db.String(20), unique=True, nullable=False)
    phone_number = db.Column(db.String(15), nullable=False)
    joining_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    monthly_fee = db.Column(db.Float, nullable=False, default=1000.0)  # Default monthly fee amount
    fees = db.relationship('FeePayment', backref='student', lazy=True, cascade="all, delete-orphan")

    def generate_monthly_fee(self, month_date=None):
        """Generate unpaid fee record for the specified month if it doesn't exist"""
        if month_date is None:
            month_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Check if fee record already exists for this month
        existing_fee = FeePayment.query.filter(
            FeePayment.student_id == self.id,
            FeePayment.month == month_date
        ).first()
        
        if not existing_fee:
            # Create new unpaid fee record
            fee = FeePayment(
                student_id=self.id,
                amount=self.monthly_fee,
                month=month_date,
                status='unpaid'
            )
            db.session.add(fee)
            return fee
        return None

class FeePayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    month = db.Column(db.DateTime, nullable=False)
    payment_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False, default='unpaid')  # paid/unpaid

def generate_fees_for_all_students():
    """Generate unpaid fee records for all students for the current month"""
    current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    students = Student.query.all()
    fees_generated = 0
    
    for student in students:
        fee = student.generate_monthly_fee(current_month)
        if fee:
            fees_generated += 1
    
    if fees_generated > 0:
        try:
            db.session.commit()
            print(f"Generated {fees_generated} new fee records for {current_month.strftime('%B %Y')}")
        except:
            db.session.rollback()
            print("Error generating fee records")

# Routes
@app.route('/')
def dashboard():
    # Generate fees for current month if not already generated
    generate_fees_for_all_students()
    
    students = Student.query.all()
    unpaid_fees = FeePayment.query.filter_by(status='unpaid').all()
    monthly_collection = sum(fee.amount for fee in FeePayment.query.filter(
        FeePayment.status == 'paid',
        FeePayment.payment_date >= datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    ).all())
    return render_template('dashboard.html', students=students, unpaid_fees=unpaid_fees, monthly_collection=monthly_collection)

@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        student = Student(
            name=request.form.get('name'),
            seat_number=request.form.get('seat_number'),
            phone_number=request.form.get('phone_number'),
            monthly_fee=float(request.form.get('monthly_fee', 1000.0))
        )
        db.session.add(student)
        try:
            db.session.commit()
            # Generate fee for current month for new student
            student.generate_monthly_fee()
            db.session.commit()
            flash('Student added successfully')
        except:
            db.session.rollback()
            flash('Error adding student. Seat number might be already taken.')
        return redirect(url_for('dashboard'))
    return render_template('add_student.html')

@app.route('/edit_student/<int:student_id>', methods=['GET', 'POST'])
def edit_student(student_id):
    student = Student.query.get_or_404(student_id)
    if request.method == 'POST':
        student.name = request.form.get('name')
        student.seat_number = request.form.get('seat_number')
        student.phone_number = request.form.get('phone_number')
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
        month = datetime.strptime(request.form.get('month'), '%Y-%m')
        # Check if fee record already exists for this month
        existing_fee = FeePayment.query.filter(
            FeePayment.student_id == student_id,
            FeePayment.month == month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        ).first()
        
        if existing_fee:
            existing_fee.amount = float(request.form.get('amount'))
            existing_fee.status = request.form.get('status', 'unpaid')
        else:
            fee = FeePayment(
                student_id=student_id,
                amount=float(request.form.get('amount')),
                month=month.replace(day=1),
                status=request.form.get('status', 'unpaid')
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
    unpaid = FeePayment.query.filter_by(status='unpaid').join(Student).order_by(FeePayment.month.desc()).all()
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
        month = datetime.strptime(request.form.get('month'), '%Y-%m')
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
    with app.app_context():
        db.create_all()
        # Generate initial fees for all students
        generate_fees_for_all_students()
    app.run(debug=True)
