from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User
import json
import random
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'exam_secret_key_enhanced'
app.config['TEMPLATES_AUTO_RELOAD'] = True

def load_questions():
    with open("questions.json", encoding="utf-8") as f:
        return json.load(f)

def select_questions(subject, topic, difficulty, num=10):
    questions_data = load_questions()
    
    if topic == "All Topics":
        all_questions = []
        for t in questions_data[subject]:
            all_questions.extend(questions_data[subject][t])
        base_pool = all_questions
    else:
        base_pool = questions_data[subject][topic]

    if difficulty == "All Levels":
        filtered = base_pool
    else:
        difficulty_level = int(difficulty)
        filtered = [q for q in base_pool if q['difficulty'] == difficulty_level]

    if len(filtered) < num:
        filtered = base_pool

    num_to_select = min(len(filtered), num)
    selected = random.sample(filtered, num_to_select)

    for question in selected:
        options = question['options'].copy()
        random.shuffle(options)
        question['options'] = options

    return selected

@app.route("/", methods=["GET", "POST"])
def index():
    questions_data = load_questions()
    subjects = {s: list(t.keys()) for s, t in questions_data.items()}

    for subject in subjects:
        subjects[subject].insert(0, "All Topics")

    if request.method == "POST":
        try:
            subject = request.form["subject"]
            topic = request.form["topic"]
            difficulty = request.form["difficulty"]
            num_questions = int(request.form.get("num_questions", 10))

            if not all([subject, topic, difficulty]):
                raise ValueError("Please select all required fields")

            selected_questions = select_questions(subject, topic, difficulty, num_questions)

            if not selected_questions:
                raise ValueError("No questions available for this selection")

            session.clear()
            session["questions"] = selected_questions
            session["current_q"] = 0
            session["answers"] = []
            session["subject"] = subject
            session["topic"] = topic
            session["difficulty"] = difficulty
            session["start_time"] = datetime.now().timestamp()

            return redirect(url_for("quiz"))

        except Exception as e:
            return render_template("index.html", subjects=subjects, error=str(e))

    return render_template("index.html", subjects=subjects)

@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    if "questions" not in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        session["answers"].append(request.form.get("option"))
        session["current_q"] += 1

        if session["current_q"] >= len(session["questions"]):
            return redirect(url_for("review"))

        return redirect(url_for("quiz"))

    current_q = session["current_q"]
    total_q = len(session["questions"])
    progress = (current_q / total_q) * 100
    question = session["questions"][current_q]

    return render_template("quiz.html",
                           question=question,
                           q_number=current_q + 1,
                           total_q=total_q,
                           progress=round(progress),
                           subject=session["subject"],
                           topic=session["topic"],
                           difficulty=session["difficulty"])

@app.route("/review")
def review():
    if "questions" not in session or "answers" not in session:
        return redirect(url_for("index"))

    if len(session["answers"]) < len(session["questions"]):
        return redirect(url_for("quiz"))

    questions = session["questions"]
    answers = session["answers"]
    review_data = []

    for i, question in enumerate(questions):
        user_answer = answers[i] if i < len(answers) else None
        review_data.append({
            "question": question["question"],
            "options": question["options"],
            "user_answer": user_answer,
            "correct_answer": question["answer"],
            "explanation": question.get("explanation", "No explanation provided."),
            "correct": user_answer == question["answer"]
        })

    return render_template("review.html",
                           review_data=review_data,
                           subject=session["subject"],
                           topic=session["topic"])

@app.route("/result")
def result():
    if "questions" not in session or "answers" not in session:
        return redirect(url_for("index"))

    questions = session["questions"]
    answers = session["answers"]
    start_time = session.get("start_time", 0)
    end_time = datetime.now().timestamp()
    duration_seconds = round(end_time - start_time)
    minutes = duration_seconds // 60
    seconds = duration_seconds % 60
    duration = f"{minutes}:{seconds:02d}"

    correct_count = 0
    review_data = []

    for i, question in enumerate(questions):
        user_answer = answers[i] if i < len(answers) else None
        is_correct = user_answer == question["answer"]

        if is_correct:
            correct_count += 1

        review_data.append({
            "q_num": i + 1,
            "question": question["question"],
            "options": question["options"],
            "user_answer": user_answer,
            "correct_answer": question["answer"],
            "explanation": question.get("explanation", "No explanation provided."),
            "is_correct": is_correct,
            "difficulty": question["difficulty"]
        })

    total = len(questions)
    percent = round((correct_count / total) * 100, 1) if total > 0 else 0

    if percent >= 90:
        message = "Excellent! You've mastered this topic."
    elif percent >= 75:
        message = "Good job! You're doing well."
    elif percent >= 60:
        message = "You're on the right track. Keep studying!"
    else:
        message = "Keep practicing. You'll improve with time."

    # Save result to session history
    quiz_record = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "subject": session.get("subject"),
        "topic": session.get("topic"),
        "difficulty": session.get("difficulty"),
        "score": correct_count,
        "total": total,
        "percentage": percent
    }

    if "quiz_history" not in session:
        session["quiz_history"] = []

    session["quiz_history"].append(quiz_record)

    return render_template("result.html",
                           score=correct_count,
                           total=total,
                           percent=percent,
                           review=review_data,
                           message=message,
                           duration=duration,
                           subject=session["subject"],
                           topic=session["topic"])

@app.route("/history")
def history():
    history_data = session.get("quiz_history", [])
    return render_template("history.html", history=history_data)

@app.route("/rate_question", methods=["POST"])
def rate_question():
    data = request.get_json()
    question_idx = data.get("question_idx")
    rating = data.get("rating")
    return jsonify({"success": True})

@app.route("/submit_feedback", methods=["POST"])
def submit_feedback():
    feedback = request.form.get("feedback")
    helpful = request.form.get("helpful")
    return redirect(url_for("result", feedback=feedback))

@app.route("/submit_site_feedback", methods=["POST"])
def submit_site_feedback():
    rating = request.form.get("site_rating")
    comment = request.form.get("site_comment")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    feedback = {
        "timestamp": timestamp,
        "rating": rating,
        "comment": comment
    }

    try:
        if os.path.exists("site_feedback.json"):
            with open("site_feedback.json", "r") as f:
                all_feedback = json.load(f)
        else:
            all_feedback = []

        all_feedback.append(feedback)

        with open("site_feedback.json", "w") as f:
            json.dump(all_feedback, f, indent=2)
    except Exception as e:
        print("Feedback save error:", e)

    return redirect(url_for("index"))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already registered. Please login.', 'warning')
            return redirect(url_for('login'))
        hashed_pw = generate_password_hash(password, method='sha256')
        new_user = User(email=email, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        flash('Signup successful. Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('index'))
        flash('Invalid credentials.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=True)
