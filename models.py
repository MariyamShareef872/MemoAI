from database import db
from datetime import datetime

# Association model with status
class FlashcardAssignment(db.Model):
    __tablename__ = 'flashcard_assignment'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    flashcard_id = db.Column(db.Integer, db.ForeignKey('flashcard.id'))
    is_learned = db.Column(db.Boolean, default=False)
    deadline = db.Column(db.Date, nullable=True)

    student = db.relationship("User", back_populates="assignments")
    flashcard = db.relationship("Flashcard", back_populates="assignments")  # ✅ back_populates


class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # 'teacher' or 'student'

    created_flashcards = db.relationship("Flashcard", backref="creator", lazy=True)
    assignments = db.relationship("FlashcardAssignment", back_populates="student")


class Flashcard(db.Model):
    __tablename__ = 'flashcard'

    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    is_learned = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deadline = db.Column(db.DateTime, nullable=True)  # ✅ optional global deadline

    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # ✅ This line was missing earlier
    assignments = db.relationship("FlashcardAssignment", back_populates="flashcard")
