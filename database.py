import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from urllib.parse import quote_plus

# Mot de passe encodé pour la base locale
password = quote_plus("Bosspapusto97@")
LOCAL_DB_URL = f"postgresql://postgres:{password}@localhost:5432/sante_db"

# Utilise DATABASE_URL si configurée (Render), sinon utilise la base locale
DATABASE_URL = os.getenv("DATABASE_URL", LOCAL_DB_URL)

# Correctif si Render fournit une URL commençant par postgres:// au lieu de postgresql://
if DATABASE_URL.startswith("postgres://"):
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