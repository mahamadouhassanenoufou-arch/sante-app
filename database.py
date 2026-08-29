from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from urllib.parse import quote_plus

# Encodage du mot de passe pour gérer les caractères spéciaux
password = quote_plus("Bosspapusto97@")
DATABASE_URL = f"postgresql://postgres:{password}@localhost:5432/sante_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

try:
    with engine.connect() as connection:
        print("Connexion à PostgreSQL réussie avec succès !")
except Exception as e:
    print(f"Erreur de connexion : {e}")

    def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()