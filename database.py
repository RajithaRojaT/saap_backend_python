from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import get_settings
from sqlalchemy.pool import QueuePool


DATABASE_URL = get_settings().database_url

# Prevents the error: "MySQL Connection not available."
# https://docs.sqlalchemy.org/en/13/core/pooling.html#pool-disconnects-pessimistic


engine = create_engine(DATABASE_URL, poolclass=QueuePool,
                       pool_size=10, max_overflow=-1, pool_timeout=30, pool_pre_ping=True, pool_recycle=3600)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker
# from sqlalchemy.ext.declarative import declarative_base

# SQLALCHEMY_DATABASE_URL = 'mysql+pymysql://root:root@127.0.0.1:3306/student_assessment'

# engine = create_engine(SQLALCHEMY_DATABASE_URL)

# SessionLocal = sessionmaker(autoflush=False, autocommit=False, bind=engine)


Base = declarative_base()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()