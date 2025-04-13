from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Schedule(Base):
    __tablename__ = 'schedules'
    id = Column(Integer, primary_key=True)
    bot_name = Column(String, nullable=False)
    schedule = Column(String, nullable=False)
    api_endpoint = Column(String, nullable=False)
    active = Column(Boolean, default=True)

class RunLog(Base):
    __tablename__ = 'run_logs'
    id = Column(Integer, primary_key=True)
    schedule_id = Column(Integer, nullable=True)
    app_name = Column(String(50), nullable=True)  # Thêm để lưu ai/kbs
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    status = Column(String(50), nullable=False)
    output = Column(String, nullable=True)
    error_message = Column(String, nullable=True)