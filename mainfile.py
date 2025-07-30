from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from database import db
from models import User, Flashcard, FlashcardAssignment, User
import os
from sqlalchemy.orm import joinedload


app = Flask(__name__)
app.secret_key = 'your_secret_key'

# DB Config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///memoai.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Create DB 
#with app.app_context():
   # db.create_all()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        role = request.form['role']

        # Check if user already exists
        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("Email already registered. Please login.")
            return render_template('register.html')

        new_user = User(name=name, email=email, password=password, role=role)
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful. Please login.")
        return render_template('register.html')


    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['role'] = user.role  
            session['name'] = user.name  
            print("[DEBUG] Logged in user session:", session)
            if user.role == 'student':
                return redirect(url_for('student_dashboard'))
            elif user.role == 'teacher':
                return redirect(url_for('teacher_dashboard'))
        else:
            flash('Invalid email or password.', 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/teacher/dashboard')
def teacher_dashboard():
    if session.get('role') != 'teacher':
        flash("Access denied.")
        return redirect(url_for('login'))

    flashcards = Flashcard.query.filter_by(teacher_id=session.get('user_id')).all()
    students = User.query.filter_by(role='student').all()
    return render_template('teacher_dashboard.html', name=session.get('name'), flashcards=flashcards, students=students)

@app.route('/teacher/create', methods=['GET', 'POST'])
def create_flashcard():
    print("[DEBUG] Accessing create_flashcard - session:", session)
    if 'user_id' not in session:
        flash("Please log in as a teacher.", "error")
        return redirect(url_for('login'))

    if request.method == 'POST':
        question = request.form.get('question')
        answer = request.form.get('answer')
        deadline_input = request.form.get('deadline')
        teacher_id = session['user_id']

        print("📅 Raw deadline input:", deadline_input)

        if not question or not answer:
            flash("Please fill out both the question and answer fields.", "error")
            return redirect(url_for('create_flashcard'))

        # ✅ Declare deadline first
        deadline = None
        if deadline_input:
            try:
                deadline = datetime.strptime(deadline_input, "%Y-%m-%d")
                print("✅ Parsed deadline:", deadline)
            except ValueError:
                flash("Invalid date format. Use YYYY-MM-DD.", "error")
                return redirect(url_for('create_flashcard'))

        # ✅ Save the flashcard first
        flashcard = Flashcard(
            question=question,
            answer=answer,
            teacher_id=teacher_id
        )
        db.session.add(flashcard)
        db.session.commit()
        if deadline:
            students = User.query.filter_by(role='student').all()
            for student in students:
                print(f"Assigning flashcard {flashcard.id} to {student.name} with deadline {deadline}")
                assignment = FlashcardAssignment(
                    flashcard_id=flashcard.id,
                    student_id=student.id,
                    deadline=deadline
                )
                db.session.add(assignment)
            db.session.commit()
        flash("✅ Flashcard created successfully!", "success")
        return redirect(url_for('create_flashcard'))

    return render_template('create_flashcard.html')

@app.route('/teacher/flashcards')
def manage_flashcards():
    if session.get('role') != 'teacher':
        flash("Access denied.")
        return redirect(url_for('login'))

    teacher_id = session.get('user_id')
    search_query = request.args.get('search', '')

    if search_query:
        flashcards = Flashcard.query.filter(
            Flashcard.teacher_id == teacher_id,
            Flashcard.question.ilike(f'%{search_query}%')
        ).all()
    else:
        flashcards = Flashcard.query.filter_by(teacher_id=teacher_id).all()

    return render_template('manage_flashcards.html', flashcards=flashcards, search_query=search_query)

@app.route('/delete_flashcard/<int:flashcard_id>', methods=['POST'])
def delete_flashcard(flashcard_id):
    if 'teacher_id' not in session:
        flash("Access denied. Please log in as a teacher.", "error")
        return redirect(url_for('login'))

    flashcard = Flashcard.query.get(flashcard_id)
    if flashcard:
        # Delete related assignments too
        FlashcardAssignment.query.filter_by(flashcard_id=flashcard_id).delete()
        db.session.delete(flashcard)
        db.session.commit()
        flash("Flashcard deleted successfully!", "success")
    else:
        flash("Flashcard not found.", "error")

    return redirect(url_for('manage_flashcards'))
    
@app.route('/teacher/edit_flashcard/<int:flashcard_id>', methods=['GET', 'POST'])
def edit_flashcard(flashcard_id):
    if 'user_id' not in session or session.get('role') != 'teacher':
        flash("Access denied. Please log in as a teacher.", "error")
        return redirect(url_for('login'))

    flashcard = Flashcard.query.get_or_404(flashcard_id)
    assignment = FlashcardAssignment.query.filter_by(flashcard_id=flashcard.id).first()

    if request.method == 'POST':
        flashcard.question = request.form.get('question')
        flashcard.answer = request.form.get('answer')

      
        deadline_input = request.form.get('deadline')
        if assignment and deadline_input:
            try:
                new_deadline = datetime.strptime(deadline_input, "%Y-%m-%d")
                assignment.deadline = new_deadline
            except ValueError:
                flash("❌ Invalid date format. Use YYYY-MM-DD.", "error")
                return redirect(url_for('edit_flashcard', flashcard_id=flashcard.id))

        db.session.commit()
        flash("✅ Flashcard updated successfully!", "success")
        return redirect(url_for('manage_flashcards'))

    return render_template('edit_flashcard.html', flashcard=flashcard, assignment=assignment)


@app.route('/teacher/assign', methods=['GET', 'POST'])
def assign_flashcards():
    if session.get('role') != 'teacher':
        flash("Access denied.")
        return redirect(url_for('login'))

    students = User.query.filter_by(role='student').all()
    flashcards = Flashcard.query.filter_by(teacher_id=session.get('user_id')).all()

    if request.method == 'POST':
        student_ids = request.form.getlist('student_ids')         # get multiple students
        selected_ids = request.form.getlist('flashcard_ids')      # get multiple flashcards

        if not student_ids or not selected_ids:
            flash("Please select at least one student and one flashcard.")
            return redirect(url_for('assign_flashcards'))

        for student_id in student_ids:
            for fid in selected_ids:
                existing = FlashcardAssignment.query.filter_by(
                    student_id=int(student_id),
                    flashcard_id=int(fid)
                ).first()
                if not existing:
                    assignment = FlashcardAssignment(
                        student_id=int(student_id),
                        flashcard_id=int(fid)
                    )
                    db.session.add(assignment)

        db.session.commit()
        flash("Flashcards assigned successfully!")
        return redirect(url_for('assign_flashcards'))

    return render_template('assign_flashcards.html', students=students, flashcards=flashcards)

@app.route('/student/dashboard')
def student_dashboard():
    if 'user_id' not in session or session.get('role') != 'student':
        flash("Access denied. Please log in as a student.", "error")
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    assignments = FlashcardAssignment.query.options(
        joinedload(FlashcardAssignment.flashcard)
    ).filter_by(student_id=user.id).all()

    for a in assignments:
        print(f"[DEBUG] Assignment ID: {a.id}, Flashcard ID: {a.flashcard.id}, Deadline: {a.flashcard.deadline}")



    return render_template('student_dashboard.html', user=user, assignments=assignments)

@app.route('/student/learned/<int:assignment_id>', methods=['POST'])
def mark_learned(assignment_id):
    assignment = FlashcardAssignment.query.get_or_404(assignment_id)
    if session.get('user_id') != assignment.student_id:
        flash("Unauthorized")
        return redirect(url_for('student_dashboard'))

    assignment.is_learned = True
    db.session.commit()
    flash("Marked as learned!")
    return redirect(url_for('student_dashboard'))

@app.route('/teacher/progress')
def view_student_progress():
    if session.get('role') != 'teacher':
        flash("Access denied.")
        return redirect(url_for('login'))

    students = User.query.filter_by(role='student').all()

    progress_data = []
    for student in students:
        assignments = student.assignments
        total = len(assignments)
        learned = sum(1 for a in assignments if a.is_learned)
        progress_data.append({
            'student': student,
            'total': total,
            'learned': learned
        })

    return render_template('student_progress.html', progress_data=progress_data)

if __name__ == '__main__':
    app.run(debug=True)
