import os
import smtplib
import traceback
from email.message import EmailMessage
from datetime import timedelta
from typing import List

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

import models, schemas, utils
from database import engine, get_db

# Recréation propre pour appliquer les nouveaux champs
with engine.connect() as conn:
    try:
        conn.execute(text("DROP TABLE IF EXISTS rendez_vous CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS creneaux CASCADE;"))
        conn.commit()
    except Exception as e:
        print(f"Info migration: {e}")

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="SantéApp API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def send_email_safe(to_email: str, subject: str, content: str):
    mail_server = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    mail_port = int(os.getenv("MAIL_PORT", 587))
    mail_user = os.getenv("MAIL_USERNAME")
    mail_pass = os.getenv("MAIL_PASSWORD")

    if not mail_user or not mail_pass:
        return

    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = mail_user
        msg["To"] = to_email
        msg.set_content(content)

        with smtplib.SMTP(mail_server, mail_port, timeout=5) as server:
            server.starttls()
            server.login(mail_user, mail_pass)
            server.send_message(msg)
    except Exception as e:
        print(f"SMTP non bloquant: {e}")


# --- AUTHENTIFICATION ---

@app.post("/api/auth/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
@app.post("/api/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    try:
        db_user = db.query(models.User).filter(models.User.email == user.email).first()
        if db_user:
            raise HTTPException(status_code=400, detail="Cet e-mail est déjà utilisé.")
        
        hashed_pwd = utils.hash_password(user.password)
        new_user = models.User(
            nom=user.nom, prenom=user.prenom, email=user.email,
            password=hashed_pwd, role=user.role,
            specialite=user.specialite, hopital=user.hopital
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        send_email_safe(new_user.email, "Bienvenue sur SantéApp", f"Bonjour {new_user.prenom},\nVotre compte a été créé.")
        return new_user
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/auth/login", response_model=schemas.Token)
@app.post("/api/login", response_model=schemas.Token)
def login(user_credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == user_credentials.email).first()
    if not user or not utils.verify_password(user_credentials.password, user.password):
        raise HTTPException(status_code=401, detail="Identifiants incorrects.")

    access_token = utils.create_access_token(data={"sub": user.email, "role": user.role})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "nom": user.nom,
        "prenom": user.prenom,
        "role": user.role
    }


# --- UTILISATEURS & MÉDECINS ---

@app.get("/api/medecins", response_model=List[schemas.UserResponse])
def get_medecins(db: Session = Depends(get_db)):
    return db.query(models.User).filter(models.User.role == "Médecin").all()


# --- CRÉNEAUX ---

@app.post("/api/creneaux", response_model=schemas.CreneauResponse, status_code=status.HTTP_201_CREATED)
def create_creneau(creneau: schemas.CreneauCreate, db: Session = Depends(get_db)):
    val_date = creneau.date_heure or creneau.date_debut
    new_creneau = models.Creneau(
        medecin_id=creneau.medecin_id,
        date_heure=val_date,
        date_debut=creneau.date_debut,
        date_fin=creneau.date_fin
    )
    db.add(new_creneau)
    db.commit()
    db.refresh(new_creneau)
    return new_creneau

@app.get("/api/creneaux/{medecin_id}", response_model=List[schemas.CreneauResponse])
def get_creneaux_medecin(medecin_id: int, db: Session = Depends(get_db)):
    return db.query(models.Creneau).filter(models.Creneau.medecin_id == medecin_id).all()


# --- RENDEZ-VOUS ---

@app.post("/api/rendez-vous", response_model=schemas.RendezVousResponse, status_code=status.HTTP_201_CREATED)
def create_rendez_vous(rdv: schemas.RendezVousCreate, db: Session = Depends(get_db)):
    new_rdv = models.RendezVous(patient_id=rdv.patient_id, creneau_id=rdv.creneau_id, motif=rdv.motif, statut="en_attente")
    db.add(new_rdv)
    db.commit()
    db.refresh(new_rdv)
    return new_rdv

@app.get("/api/rendez-vous/patient/{patient_id}", response_model=List[schemas.RendezVousResponse])
def get_rdv_patient(patient_id: int, db: Session = Depends(get_db)):
    return db.query(models.RendezVous).filter(models.RendezVous.patient_id == patient_id).all()


# --- FRONTEND STATIC ---
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root():
    return FileResponse("static/index.html")