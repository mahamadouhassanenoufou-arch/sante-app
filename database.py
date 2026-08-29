import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from urllib.parse import quote_plus

# Base locale de secours
password = quote_plus("Bosspapusto97@")
LOCAL_DB_URL = f"postgresql://postgres:{password}@localhost:5432/sante_db"

# Force la lecture de la variable Render
DATABASE_URL = os.environ.get("DATABASE_URL", LOCAL_DB_URL)

# Correction du préfixe postgres:// pour SQLAlchemy
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()