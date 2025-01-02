from app import app, db, generate_fees_for_all_students

with app.app_context():
    db.create_all()
    generate_fees_for_all_students()
