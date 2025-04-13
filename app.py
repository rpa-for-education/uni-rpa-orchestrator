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

# Cấu hình logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", 'rpa_orchestrator_secret_key_2025')

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
try:
    init_db()
    logger.debug("Database initialized")
except Exception as e:
    logger.error(f"Failed to initialize database: {str(e)}")
    raise

@app.route("/login", methods=["GET", "POST"])
def login():
    logger.debug("Accessing /login")
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
    logger.debug("Accessing /logout")
    logout_user()
    flash("Đăng xuất thành công!", "success")
    return redirect(url_for('login'))

@app.route("/")
@login_required
def index():
    logger.debug("Accessing /")
    session = SESSION()
    try:
        # Query schedules
        schedules = session.query(Schedule).all()
        logger.debug(f"Loaded {len(schedules)} schedules")
        if not schedules:
            logger.warning("No schedules found, adding sample")
            sample_schedule = Schedule(
                bot_name="Sample Bot",
                schedule="*/5 * * * *",
                api_endpoint="https://jsonplaceholder.typicode.com/todos/1",
                active=True
            )
            session.add(sample_schedule)
            session.commit()
            schedules = [sample_schedule]

        # Query logs
        logs = session.query(RunLog).order_by(RunLog.start_time.desc()).limit(10).all()
        logger.debug(f"Loaded {len(logs)} logs")

        # Query stats
        active_schedules = session.query(Schedule).filter_by(active=True).count()
        total_runs = session.query(RunLog).count()
        ai_log = session.query(RunLog).filter_by(app_name="ai").order_by(RunLog.start_time.desc()).first()
        kbs_log = session.query(RunLog).filter_by(app_name="kbs").order_by(RunLog.start_time.desc()).first()
        ai_status = ai_log.status if ai_log else "N/A"
        kbs_status = kbs_log.status if kbs_log else "N/A"
        logger.debug(f"Stats: active_schedules={active_schedules}, total_runs={total_runs}, ai_status={ai_status}, kbs_status={kbs_status}")

        return render_template(
            "index.html",
            schedules=schedules,
            logs=logs,
            active_schedules=active_schedules,
            total_runs=total_runs,
            ai_status=ai_status,
            kbs_status=kbs_status
        )
    except Exception as e:
        logger.error(f"Error in index: {str(e)}")
        flash("Lỗi khi tải trang chủ", "danger")
        return render_template(
            "index.html",
            schedules=[],
            logs=[],
            active_schedules=0,
            total_runs=0,
            ai_status="N/A",
            kbs_status="N/A"
        )
    finally:
        try:
            session.close()
        except Exception as e:
            logger.error(f"Failed to close session: {str(e)}")

@app.route("/trigger_github_ai", methods=["POST"])
@login_required
def trigger_ai():
    logger.debug("Received request to /trigger_github_ai")
    try:
        action = request.form.get('action', 'start')
        logger.debug(f"Triggering AI with action: {action}")
        run_bot('ai', action)
        logger.debug("run_bot for AI completed")
        return jsonify({"message": f"Triggered {action} for AI"})
    except Exception as e:
        logger.error(f"Error in trigger_ai: {str(e)}")
        return jsonify({"message": f"Error triggering AI: {str(e)}"}), 500

@app.route("/trigger_github_kbs", methods=["POST"])
@login_required
def trigger_kbs():
    logger.debug("Received request to /trigger_github_kbs")
    try:
        action = request.form.get('action', 'start')
        logger.debug(f"Triggering KBS with action: {action}")
        run_bot('kbs', action)
        logger.debug("run_bot for KBS completed")
        return jsonify({"message": f"Triggered {action} for KBS"})
    except Exception as e:
        logger.error(f"Error in trigger_kbs: {str(e)}")
        return jsonify({"message": f"Error triggering KBS: {str(e)}"}), 500

@app.route("/api/stats", methods=["GET"])
@login_required
def stats():
    logger.debug("Accessing /api/stats")
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
        logger.error(f"Error in stats: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            session.close()
        except Exception as e:
            logger.error(f"Failed to close session: {str(e)}")

@app.route("/api/logs", methods=["GET"])
@login_required
def get_logs():
    logger.debug("Accessing /api/logs")
    session = SESSION()
    try:
        logs = session.query(RunLog).order_by(RunLog.start_time.desc()).limit(10).all()
        return jsonify([
            {
                "app_name": log.app_name or "N/A",
                "start_time": log.start_time.isoformat(),
                "end_time": log.end_time.isoformat() if log.end_time else "",
                "status": log.status,
                "output": log.output or "",
                "error_message": log.error_message or ""
            } for log in logs
        ])
    except Exception as e:
        logger.error(f"Error in get_logs: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            session.close()
        except Exception as e:
            logger.error(f"Failed to close session: {str(e)}")

if __name__ == "__main__":
    logger.debug("Starting application")
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
            logger.debug("Sample schedule added")
    except Exception as e:
        logger.error(f"Error initializing sample schedule: {str(e)}")
        session.rollback()
    finally:
        try:
            session.close()
        except Exception as e:
            logger.error(f"Failed to close session: {str(e)}")

    try:
        load_schedules()
        start_scheduler()
    except Exception as e:
        logger.error(f"Error starting scheduler: {str(e)}")

    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)