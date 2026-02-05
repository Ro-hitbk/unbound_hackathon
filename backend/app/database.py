# app/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Check for Railway environment (uses SQLite) vs local (uses MySQL)
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Railway: Use SQLite file in /tmp for persistence
    DATABASE_URL = "sqlite:///./workflows.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # Local: Use MySQL
    DATABASE_URL = "mysql+pymysql://root:mascaradancer@localhost:3306/unbounddb"
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
