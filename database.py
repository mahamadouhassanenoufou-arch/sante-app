import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Mettez directement vos accès PostgreSQL ici
# Format: postgresql://UTILISATEUR:MOT_DE_PASSE@localhost:5432/NOM_DB
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:Bosspapusto97%40@localhost:5432/sante_db"

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