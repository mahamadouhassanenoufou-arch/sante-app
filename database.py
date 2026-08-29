import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from urllib.parse import quote_plus

# Base de données locale de secours
password = quote_plus("Bosspapusto97@")
LOCAL_DB_URL = f"postgresql://postgres:{password}@localhost:5432/sante_db"

# Récupération de l'URL cloud de Render
DATABASE_URL = os.environ.get("DATABASE_URL", LOCAL_DB_URL)

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