import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

database_url = os.getenv("DATABASE_URL", "sqlite:///orchestrator.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
engine = create_engine(database_url, echo=False)
Base.metadata.create_all(engine)
SessionFactory = sessionmaker(bind=engine)