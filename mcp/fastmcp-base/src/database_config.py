# Database configuration for Alembic

import os
from sqlalchemy import create_engine, MetaData

# 데이터베이스 URL
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:password@localhost:5432/fastmcp_db"
)

# SQLAlchemy 엔진
engine = create_engine(DATABASE_URL)
metadata = MetaData()

# 테이블 이름 접두사
TABLE_PREFIX = "fastmcp_"
