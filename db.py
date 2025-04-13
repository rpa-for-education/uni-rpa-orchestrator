import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from models import Base

# Lấy DATABASE_URL từ biến môi trường
database_url = os.getenv("DATABASE_URL")
if not database_url:
    raise ValueError("DATABASE_URL is not set. Please configure it in Vercel environment variables.")

# Thay postgres:// thành postgresql:// cho SQLAlchemy
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

# Cấu hình engine với connection pool tối ưu cho Neon
engine = create_engine(
    database_url,
    echo=False,  # Không log SQL queries
    pool_size=5,  # Số kết nối tối đa trong pool
    max_overflow=10,  # Số kết nối bổ sung nếu pool đầy
    pool_timeout=30,  # Thời gian chờ kết nối
    connect_args={
        "connect_timeout": 10,  # Timeout kết nối đến Neon
        "sslmode": "require"  # Bắt buộc SSL cho Neon
    }
)

# Tạo session factory
SessionFactory = sessionmaker(bind=engine)

# Dùng scoped_session để quản lý session theo thread
SESSION = scoped_session(SessionFactory)

# Hàm khởi tạo bảng
def init_db():
    """Tạo tất cả bảng trong database nếu chưa tồn tại."""
    Base.metadata.create_all(engine)

# Hàm để lấy session mới (dùng trong github_trigger.py hoặc scheduler.py)
def get_session():
    """Trả về session mới, cần đóng sau khi dùng."""
    return SESSION()