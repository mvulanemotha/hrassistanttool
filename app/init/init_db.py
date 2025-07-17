from app.database.database import engine , Base
from app.models.user_model import User # import user model


if __name__ == "__main__":
    print("📦 Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")