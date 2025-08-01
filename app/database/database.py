from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker , declarative_base

#SQLite database will be stored in a local file named app.db
#SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"

SQLALCHEMY_DATABASE_URL = "postgresql://Mkhululi:Mvulane9876543210@158.220.117.250:5432/hraiassistant"

# for sqlite , connect_args is needed to allow multi-thread access
engine = create_engine(
    #SQLALCHEMY_DATABASE_URL , connect_args={"check_same_thread": False}
    SQLALCHEMY_DATABASE_URL
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()