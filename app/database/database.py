from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker , declarative_base

#SQLite database will be stored in a local file named app.db
SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"

# for sqlite , connect_args is needed to allow multi-thread access
engine = create_engine(
    SQLALCHEMY_DATABASE_URL , connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()