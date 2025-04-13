import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from db import SessionFactory, SESSION, init_db
from models import Schedule, RunLog
from scheduler import start_scheduler, load_schedules, run_bot
from github_trigger import trigger_github_action
from sqlalchemy import func
from datetime import datetime, timedelta
import logging
import bcrypt
import sys

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", 'rpa_orchestrator_secret_key_2025')

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

users = {
    'admin': {
        'password': bcrypt.hashpw('Neu@2025'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    }
}

class User(UserMixin):
    def __init__(self, username):
        self.id = username

@login_manager.user_loader
def load_user(username):
    if username in users:
        return User(username)
    return None

# Khởi tạo bảng
init_db()

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username in users and bcrypt.checkpw(password.encode('utf-8'), users[username]['password'].encode('utf-8')):
            user = User(username)
            login_user(user)
            flash("Đăng nhập thành công!", "success")
            return redirect(url_for('index'))
        else:
            flash("Sai tài khoản hoặc mật khẩu", "danger")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Đăng xuất thành công!", "success")
    return redirect(url_for('login'))

@app.route("/")
@login_required
def index():
    session = SESSION()
    try:
        schedules = session.query(Schedule).all()
        logs = session.query(RunLog).order_by(RunLog.start_time.desc()).limit(10).all()
        active_schedules = session.query(Schedule).filter_by(active=True).count()
        total_runs = session.query(RunLog).count()
        ai_log = session.query(RunLog).filter_by(app_name="ai").order_by(RunLog.start_time.desc()).first()
        kbs_log = session.query(RunLog).filter_by(app_name="kbs").order_by(RunLog.start_time.desc()).first()
        ai_status = ai_log.status if ai_log else "N/A"
        kbs_status = kbs_log.status if kbs_log else "N/A"
        return render_template(
            "index.html",
            schedules=schedules,
            logs=logs,
            active_schedules=active_schedules,
            total_runs=total_runs,
            ai_status=ai_status,
            kbs_status=kbs_status
        )
    finally:
        session.close()

@app.route("/trigger_github_ai", methods=["POST"])
@login_required
def trigger_ai():
    action = request.form.get('action', 'start')
    run_bot('ai', action)
    return jsonify({"message": f"Triggered {action} for AI"})

@app.route("/trigger_github_kbs", methods=["POST"])
@login_required
def trigger_kbs():
    action = request.form.get('action', 'start')
    run_bot('kbs', action)
    return jsonify({"message": f"Triggered {action} for KBS"})

@app.route("/api/stats", methods=["GET"])
@login_required
def stats():
    session = SESSION()
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
        status_counts = session.query(
            RunLog.status,
            func.count(RunLog.id)
        ).filter(
            RunLog.start_time >= start_date
        ).group_by(RunLog.status).all()
        status_data = {status: count for status, count in status_counts}
        date_counts = session.query(
            func.date(RunLog.start_time),
            func.count(RunLog.id)
        ).filter(
            RunLog.start_time >= start_date
        ).group_by(func.date(RunLog.start_time)).all()
        date_data = {str(date): count for date, count in date_counts}
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            if date_str not in date_data:
                date_data[date_str] = 0
            current_date += timedelta(days=1)
        return jsonify({
            "status_counts": status_data,
            "date_counts": date_data
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()

if __name__ == "__main__":
    session = SESSION()
    try:
        if not session.query(Schedule).first():
            sample_schedule = Schedule(
                bot_name="Sample Bot",
                schedule="*/5 * * * *",
                api_endpoint="https://jsonplaceholder.typicode.com/todos/1",
                active=True
            )
            session.add(sample_schedule)
            session.commit()
    except Exception as e:
        print(f"Error initializing sample schedule: {e}")
        session.rollback()
    finally:
        session.close()

    try:
        load_schedules()
        start_scheduler()
    except Exception as e:
        print(f"Error starting scheduler: {e}")

    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)