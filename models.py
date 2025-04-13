from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class Schedule(Base):
    __tablename__ = 'schedules'
    id = Column(Integer, primary_key=True)
    bot_name = Column(String)
    schedule = Column(String)  # Cron expression, e.g., "*/5 * * *"
    api_endpoint = Column(String)
    active = Column(Boolean, default=True)

class RunLog(Base):
    __tablename__ = 'run_logs'
    id = Column(Integer, primary_key=True)
    schedule_id = Column(Integer)
    start_time = Column(DateTime, default=datetime.datetime.utcnow)
    end_time = Column(DateTime)
    status = Column(String)
    error_message = Column(String)
    output = Column(String)