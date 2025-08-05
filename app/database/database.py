from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker , declarative_base
from dotenv import load_dotenv
import os

#SQLite database will be stored in a local file named app.db
#SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

SQLALCHEMY_DATABASE_URL = DATABASE_URL

# for sqlite , connect_args is needed to allow multi-thread access
engine = create_engine(
    #SQLALCHEMY_DATABASE_URL , connect_args={"check_same_thread": False}
    SQLALCHEMY_DATABASE_URL
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()