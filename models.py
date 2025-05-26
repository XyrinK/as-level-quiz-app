from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    xyrinpoints = db.Column(db.Integer, default=0)  # for future gamification
class QuizHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(100))
    topic = db.Column(db.String(100))
    difficulty = db.Column(db.String(20))
    score = db.Column(db.Integer)
    total = db.Column(db.Integer)
    percentage = db.Column(db.Float)
    timestamp = db.Column(db.String(50))

User.history = db.relationship('QuizHistory', backref='user', lazy=True)
