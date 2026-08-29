import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Récupération de l'URL depuis l'environnement
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# Correction du préfixe 'postgres://' en 'postgresql://' si nécessaire
if SQLALCHEMY_DATABASE_URL and SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Ajout de sslmode=require si absente
if SQLALCHEMY_DATABASE_URL and "sslmode=" not in SQLALCHEMY_DATABASE_URL:
    if "?" in SQLALCHEMY_DATABASE_URL:
        SQLALCHEMY_DATABASE_URL += "&sslmode=require"
    else:
        SQLALCHEMY_DATABASE_URL += "?sslmode=require"

# Création de l'engine avec ping automatique du pool
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()