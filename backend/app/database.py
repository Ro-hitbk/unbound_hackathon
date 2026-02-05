# app/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Use DATABASE_URL env var if set (Railway), otherwise use local defaults
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:mascaradancer@localhost:3306/unbounddb"
)

# Railway provides mysql:// but SQLAlchemy needs mysql+pymysql://
if DATABASE_URL.startswith("mysql://"):
    DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+pymysql://", 1)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
