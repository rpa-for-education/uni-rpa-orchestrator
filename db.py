import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from models import Base
import logging

logger = logging.getLogger(__name__)

# Lấy DATABASE_URL từ biến môi trường
database_url = os.getenv("DATABASE_URL")
if not database_url:
    logger.error("DATABASE_URL is not set")
    raise ValueError("DATABASE_URL is not set. Please configure it in Vercel environment variables.")

# Thay postgres:// thành postgresql:// cho SQLAlchemy
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

# Cấu hình engine với connection pool tối ưu cho Neon
try:
    engine = create_engine(
        database_url,
        echo=False,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        connect_args={
            "connect_timeout": 15,  # Tăng timeout
            "sslmode": "require"
        }
    )
    logger.debug("Database engine created")
except Exception as e:
    logger.error(f"Failed to create database engine: {str(e)}")
    raise

# Tạo session factory
SessionFactory = sessionmaker(bind=engine)

# Dùng scoped_session để quản lý session theo thread
SESSION = scoped_session(SessionFactory)

# Hàm khởi tạo bảng
def init_db():
    logger.debug("Initializing database tables")
    try:
        Base.metadata.create_all(engine)
        logger.debug("Database tables created")
    except Exception as e:
        logger.error(f"Failed to create tables: {str(e)}")
        raise

# Hàm để lấy session mới
def get_session():
    logger.debug("Creating new session")
    return SESSION()