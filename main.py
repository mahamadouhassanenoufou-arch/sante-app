import os
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

import models
import schemas
import security
from database import get_db, engine

# Création des tables DB & Auto-migration des colonnes manquantes
try:
    models.Base.metadata.create_all(bind=engine)
    
    # Correction automatique du schéma Postgres si des colonnes manquent dans 'consultations'
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE consultations ADD COLUMN IF NOT EXISTS date TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"))
        conn.execute(text("ALTER TABLE consultations ADD COLUMN IF NOT EXISTS prescription TEXT;"))
        conn.commit()
    print("Base de données synchronisée avec succès.")
except Exception as e:
    print(f"Note/Erreur DB sync: {e}")

app = FastAPI(title="Santé App API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    possible_paths = ["static/index.html", "index.html"]
    for path in possible_paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
    return "<h1>index.html non trouve</h1>"

@app.post("/api/auth/register", response_model=schemas.UserOut)
def register_user(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    try:
        db_user = db.query(models.User).filter(models.User.email == user_in.email).first()
        if db_user:
            raise HTTPException(status_code=400, detail="Cet email est déjà enregistré.")
        
        hashed_pwd = security.get_password_hash(user_in.password)
        
        new_user = models.User(
            nom=user_in.nom,
            prenom=user_in.prenom,
            email=user_in.email,
            hashed_password=hashed_pwd,
            role=user_in.role
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur serveur DB/Hash: {str(e)}")

@app.post("/api/auth/login", response_model=schemas.Token)
def login(user_credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    try:
        user = db.query(models.User).filter(models.User.email == user_credentials.email).first()
        if not user or not security.verify_password(user_credentials.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou mot de passe incorrect"
            )
        
        access_token = security.create_access_token(data={"sub": user.email, "role": str(user.role)})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "role": str(user.role),
            "nom": user.nom,
            "prenom": user.prenom
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur connexion: {str(e)}")

@app.get("/api/medecin/rdv", response_model=List[schemas.RdvOut])
def get_medecin_rdv(db: Session = Depends(get_db)):
    rdvs = db.query(models.RendezVous).all()
    result = []
    for r in rdvs:
        patient = db.query(models.User).filter(models.User.id == r.patient_id).first()
        result.append({
            "id": r.id,
            "date_heure": r.date_heure,
            "motif": r.motif,
            "statut": str(r.statut.value) if hasattr(r.statut, 'value') else str(r.statut),
            "patient_id": r.patient_id,
            "nom_patient": patient.nom if patient else "Inconnu",
            "prenom_patient": patient.prenom if patient else ""
        })
    return result

@app.post("/api/medecin/consultation", response_model=schemas.ConsultationOut)
def create_consultation(data: schemas.ConsultationCreate, db: Session = Depends(get_db)):
    try:
        rdv = db.query(models.RendezVous).filter(models.RendezVous.id == data.rdv_id).first()
        if not rdv:
            raise HTTPException(status_code=404, detail="Rendez-vous introuvable")

        consultation = models.Consultation(
            rdv_id=data.rdv_id,
            symptomes=data.symptomes,
            diagnostic=data.diagnostic,
            prescription=data.prescription
        )
        
        rdv.statut = "TERMINE"
        
        db.add(consultation)
        db.commit()
        db.refresh(consultation)
        return consultation
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur enregistrement consultation: {str(e)}")

@app.post("/api/dev/seed-rdv")
def seed_rdv(db: Session = Depends(get_db)):
    try:
        medecin = db.query(models.User).filter(models.User.role == "MEDECIN").first()
        patient = db.query(models.User).filter(models.User.role == "PATIENT").first()

        if not patient:
            patient = models.User(
                nom="Diallo",
                prenom="Amadou",
                email="patient.test@example.com",
                hashed_password=security.get_password_hash("password123"),
                role="PATIENT"
            )
            db.add(patient)
            db.commit()
            db.refresh(patient)

        if not medecin:
            return {"error": "Aucun médecin trouvé."}

        rdv1 = models.RendezVous(
            motif="Consultation générale",
            statut="EN_ATTENTE",
            patient_id=patient.id,
            medecin_id=medecin.id
        )
        rdv2 = models.RendezVous(
            motif="Suivi bilan de santé",
            statut="EN_ATTENTE",
            patient_id=patient.id,
            medecin_id=medecin.id
        )

        db.add_all([rdv1, rdv2])
        db.commit()
        return {"message": "Rendez-vous de test créés avec succès !"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur seed: {str(e)}")