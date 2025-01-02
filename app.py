import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
import calendar
from dateutil.relativedelta import relativedelta
from report_generator import generate_student_report, generate_monthly_report
from logger_config import setup_logger
from sqlalchemy import and_, exists

# Set up logger
logger = setup_logger()

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
        logger.info('Fees generated for all students')
    except Exception as e:
        logger.error(f'Error generating fees: {str(e)}', exc_info=True)
        db.session.rollback()

# Routes
@app.route('/')
def dashboard():
    try:
        # Generate fees for current month if not already generated
        generate_fees_for_all_students()
        
        students = Student.query.all()
        
        # Get unpaid fees with student information
        unpaid_fees = db.session.query(Fee, Student)\
            .join(Student)\
            .filter(Fee.paid == False)\
            .order_by(Student.name, Fee.month)\
            .all()
            
        # Get paid fees with student information (last 30 entries)
        paid_fees = db.session.query(Fee, Student)\
            .join(Student)\
            .filter(Fee.paid == True)\
            .order_by(Fee.payment_date.desc())\
            .limit(30)\
            .all()
            
        # Calculate monthly collection
        current_month_start = datetime.now().date().replace(day=1)
        monthly_collection = db.session.query(db.func.sum(Fee.amount))\
            .filter(
                Fee.paid == True,
                Fee.payment_date >= current_month_start
            ).scalar() or 0
            
        # Get fees due today
        today = datetime.now().date()
        current_month = today.replace(day=1)
        
        # First, get all students who haven't paid for the current month
        unpaid_students = db.session.query(Student)\
            .outerjoin(Fee, and_(
                Fee.student_id == Student.id,
                Fee.month == current_month,
                Fee.paid == True
            ))\
            .filter(Fee.id == None)\
            .all()
            
        # Then get their unpaid fees
        due_today = []
        for student in unpaid_students:
            unpaid_fee = db.session.query(Fee)\
                .filter(
                    Fee.student_id == student.id,
                    Fee.month == current_month,
                    Fee.paid == False
                ).first()
            if unpaid_fee:
                due_today.append((unpaid_fee, student))
            
        logger.info('Dashboard accessed successfully')
        return render_template('dashboard.html', 
                            students=students, 
                            unpaid_fees=unpaid_fees,
                            paid_fees=paid_fees,
                            due_today=due_today,
                            monthly_collection=monthly_collection,
                            today=today)
    except Exception as e:
        logger.error(f'Error accessing dashboard: {str(e)}', exc_info=True)
        flash('Error loading dashboard', 'error')
        return redirect(url_for('dashboard'))

@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        try:
            joining_date_str = request.form.get('joining_date')
            if not joining_date_str:
                logger.warning('Add student attempt failed: Missing joining date')
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
            
            logger.info(f'New student added successfully: {student.name} (ID: {student.id})')
            
            # Generate fee for current month for new student
            generate_fees_for_all_students()
            flash('Student added successfully', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            logger.error(f'Error adding student: {str(e)}', exc_info=True)
            flash(f'Error adding student: {str(e)}', 'error')
            return redirect(url_for('add_student'))
    
    return render_template('add_student.html')

@app.route('/edit_student/<int:student_id>', methods=['GET', 'POST'])
def edit_student(student_id):
    student = Student.query.get_or_404(student_id)
    if request.method == 'POST':
        try:
            joining_date_str = request.form.get('joining_date')
            if not joining_date_str:
                logger.warning(f'Edit student attempt failed: Missing joining date for student ID {student_id}')
                flash('Joining date is required', 'error')
                return redirect(url_for('edit_student', student_id=student_id))

            student.name = request.form.get('name')
            student.seat_number = request.form.get('seat_number')
            student.phone_number = request.form.get('phone_number')
            student.joining_date = datetime.strptime(joining_date_str, '%Y-%m-%d').date()
            student.monthly_fee = float(request.form.get('monthly_fee', student.monthly_fee))
            
            db.session.commit()
            logger.info(f'Student updated successfully: {student.name} (ID: {student.id})')
            flash('Student updated successfully', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            logger.error(f'Error updating student ID {student_id}: {str(e)}', exc_info=True)
            flash(f'Error updating student: {str(e)}', 'error')
            return redirect(url_for('edit_student', student_id=student_id))
    
    return render_template('edit_student.html', student=student)

@app.route('/delete_student/<int:student_id>', methods=['POST'])
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    try:
        name = student.name
        db.session.delete(student)
        db.session.commit()
        logger.info(f'Student deleted successfully: {name} (ID: {student_id})')
        flash('Student deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Error deleting student ID {student_id}: {str(e)}', exc_info=True)
        flash(f'Error deleting student: {str(e)}', 'error')
    return redirect(url_for('dashboard'))

@app.route('/add_fee/<int:student_id>', methods=['GET', 'POST'])
def add_fee(student_id):
    student = Student.query.get_or_404(student_id)
    if request.method == 'POST':
        try:
            month_str = request.form.get('month')
            payment_date_str = request.form.get('payment_date')
            is_paid = request.form.get('paid') == 'True'
            
            if not month_str:
                logger.warning(f'Add fee attempt failed: Missing month for student ID {student_id}')
                flash('Month is required', 'error')
                return redirect(url_for('add_fee', student_id=student_id))
                
            if not payment_date_str and is_paid:
                logger.warning(f'Add fee attempt failed: Missing payment date for paid fee (student ID {student_id})')
                flash('Payment date is required for paid fees', 'error')
                return redirect(url_for('add_fee', student_id=student_id))

            # Convert month string (YYYY-MM) to date object
            month = datetime.strptime(month_str + '-01', '%Y-%m-%d').date()
            amount = float(request.form.get('amount', student.monthly_fee))
            
            # Check if fee record already exists for this month
            existing_fee = Fee.query.filter(
                Fee.student_id == student_id,
                Fee.month == month
            ).first()
            
            if existing_fee:
                existing_fee.amount = amount
                existing_fee.paid = is_paid
                if payment_date_str:
                    existing_fee.payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date()
                elif not is_paid:
                    existing_fee.payment_date = None
                logger.info(f'Fee record updated for student ID {student_id}: Month {month_str}, Paid: {is_paid}')
            else:
                fee = Fee(
                    student_id=student_id,
                    amount=amount,
                    month=month,
                    paid=is_paid,
                    payment_date=datetime.strptime(payment_date_str, '%Y-%m-%d').date() if payment_date_str and is_paid else None
                )
                db.session.add(fee)
                logger.info(f'New fee record added for student ID {student_id}: Month {month_str}, Paid: {is_paid}')
            
            db.session.commit()
            flash('Fee payment updated successfully', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            logger.error(f'Error adding fee for student ID {student_id}: {str(e)}', exc_info=True)
            flash(f'Error adding fee payment: {str(e)}', 'error')
            return redirect(url_for('add_fee', student_id=student_id))
    
    today = datetime.now().date().strftime('%Y-%m-%d')
    return render_template('add_fee.html', student=student, today=today)

@app.route('/student/<int:student_id>')
def student_details(student_id):
    try:
        student = Student.query.get_or_404(student_id)
        logger.info(f'Student details accessed successfully: {student.name} (ID: {student_id})')
        return render_template('student_details.html', student=student)
    except Exception as e:
        logger.error(f'Error accessing student details: {str(e)}', exc_info=True)
        flash('Error loading student details', 'error')
        return redirect(url_for('index'))

@app.route('/unpaid_fees')
def unpaid_fees():
    # Generate fees for current month if not already generated
    generate_fees_for_all_students()
    
    try:
        # Get all students with unpaid fees
        unpaid = Fee.query.filter_by(paid=False).join(Student).order_by(Fee.month.desc()).all()
        logger.info('Unpaid fees accessed successfully')
        return render_template('unpaid_fees.html', unpaid_fees=unpaid)
    except Exception as e:
        logger.error(f'Error accessing unpaid fees: {str(e)}', exc_info=True)
        flash('Error loading unpaid fees', 'error')
        return redirect(url_for('index'))

@app.route('/generate_student_report/<int:student_id>')
def generate_student_report_route(student_id):
    try:
        student = Student.query.get_or_404(student_id)
        filename = f'reports/student_{student.seat_number}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        
        # Create reports directory if it doesn't exist
        os.makedirs('reports', exist_ok=True)
        
        # Generate the report
        generate_student_report(student, student.fees, filename)
        
        # Send the file to the user
        logger.info(f'Student report generated successfully: {student.name} (ID: {student_id})')
        return send_file(filename, as_attachment=True)
    except Exception as e:
        logger.error(f'Error generating student report: {str(e)}', exc_info=True)
        flash('Error generating student report', 'error')
        return redirect(url_for('index'))

@app.route('/generate_monthly_report', methods=['GET', 'POST'])
def generate_monthly_report_route():
    if request.method == 'POST':
        try:
            month = datetime.strptime(request.form.get('month'), '%Y-%m').date()
            filename = f'reports/monthly_report_{month.strftime("%Y%m")}.pdf'
            
            # Create reports directory if it doesn't exist
            os.makedirs('reports', exist_ok=True)
            
            # Get all students
            students = Student.query.order_by(Student.seat_number).all()
            
            # Generate the report
            generate_monthly_report(students, month, filename)
            
            # Send the file to the user
            logger.info(f'Monthly report generated successfully: {month.strftime("%Y-%m")}')
            return send_file(filename, as_attachment=True)
        except Exception as e:
            logger.error(f'Error generating monthly report: {str(e)}', exc_info=True)
            flash('Error generating monthly report', 'error')
            return redirect(url_for('index'))
    
    return render_template('generate_monthly_report.html')

@app.errorhandler(404)
def not_found_error(error):
    logger.warning(f'Page not found: {request.url}')
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    logger.error(f'Server Error: {str(error)}', exc_info=True)
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True)
