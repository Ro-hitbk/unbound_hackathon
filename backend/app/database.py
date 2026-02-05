# app/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Use DATABASE_URL env var if set (Railway), otherwise use local defaults
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:mascaradancer@localhost:3306/unbounddb"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
