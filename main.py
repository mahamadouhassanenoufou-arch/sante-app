import os
import smtplib
import traceback
from email.message import EmailMessage
from datetime import timedelta

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

import models, schemas, utils
from database import engine, get_db
from typing import List

# --- RESET AUTOMATIQUE DE LA TABLE OBSOLÈTE ET RECRÉATION ---
with engine.connect() as conn:
    try:
        # Supprime la table obsolète si la colonne 'password' manque
        conn.execute(text("DROP TABLE IF EXISTS users CASCADE;"))
        conn.commit()
    except Exception as e:
        print(f"Info migration: {e}")

# Re-création des tables à jour dans PostgreSQL
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


# --- ROUTES AUTHENTIFICATION ---

@app.post("/api/auth/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
@app.post("/api/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    try:
        db_user = db.query(models.User).filter(models.User.email == user.email).first()
        if db_user:
            raise HTTPException(status_code=400, detail="Cet e-mail est déjà utilisé.")
        
        hashed_pwd = utils.hash_password(user.password)
        
        new_user = models.User(
            nom=user.nom,
            prenom=user.prenom,
            email=user.email,
            password=hashed_pwd,
            role=user.role,
            specialite=user.specialite,
            hopital=user.hopital
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        send_email_safe(
            to_email=new_user.email,
            subject="Bienvenue sur SantéApp",
            content=f"Bonjour {new_user.prenom},\n\nVotre compte a été créé avec succès."
        )

        return new_user
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print("CRASH REGISTRATION:", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")


@app.post("/api/auth/login", response_model=schemas.Token)
@app.post("/api/login", response_model=schemas.Token)
def login(user_credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    try:
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
    except HTTPException:
        raise
    except Exception as e:
        print("CRASH LOGIN:", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Erreur de connexion: {str(e)}")
@app.post("/api/forgot-password")
def forgot_password(payload: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user:
        return {"message": "Si l'adresse existe, un e-mail de réinitialisation a été envoyé."}
    
    reset_token = utils.create_access_token(data={"sub": user.email}, expires_delta=timedelta(minutes=15))
    send_email_safe(
        to_email=user.email,
        subject="Réinitialisation de votre mot de passe",
        content=f"Voici votre jeton : {reset_token}"
    )
    return {"message": "Si l'adresse existe, un e-mail de réinitialisation a été envoyé."}


@app.post("/api/reset-password")
def reset_password(payload: schemas.ResetPasswordConfirm, db: Session = Depends(get_db)):
    email = utils.verify_token(payload.token)
    if not email:
        raise HTTPException(status_code=400, detail="Jeton invalide ou expiré.")

    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable.")

    user.password = utils.hash_password(payload.new_password)
    db.commit()
    return {"message": "Mot de passe réinitialisé avec succès."}


# --- ROUTES CRÉNEAUX ET RENDEZ-VOUS ---

@app.post("/api/creneaux", response_model=schemas.CreneauResponse, status_code=status.HTTP_201_CREATED)
def create_creneau(creneau: schemas.CreneauCreate, db: Session = Depends(get_db)):
    new_creneau = models.Creneau(**creneau.dict())
    db.add(new_creneau)
    db.commit()
    db.refresh(new_creneau)
    return new_creneau


@app.post("/api/rendez-vous", response_model=schemas.RendezVousResponse, status_code=status.HTTP_201_CREATED)
def create_rendez_vous(rdv: schemas.RendezVousCreate, db: Session = Depends(get_db)):
    new_rdv = models.RendezVous(**rdv.dict(), statut="en_attente")
    db.add(new_rdv)
    db.commit()
    db.refresh(new_rdv)
    return new_rdv


# --- FRONTEND ---
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root():
    return FileResponse("static/index.html")

# --- ROUTE OBTENTION DES MÉDECINS ---

@app.get("/api/medecins", response_model=List[schemas.UserResponse])
def get_medecins(db: Session = Depends(get_db)):
    # Récupère tous les utilisateurs enregistrés avec le rôle 'Médecin'
    medecins = db.query(models.User).filter(models.User.role == "Médecin").all()
    return medecins


# --- ROUTES LECTURE CRÉNEAUX ET RENDEZ-VOUS ---

@app.get("/api/creneaux/{medecin_id}", response_model=List[schemas.CreneauResponse])
def get_creneaux_medecin(medecin_id: int, db: Session = Depends(get_db)):
    creneaux = db.query(models.Creneau).filter(models.Creneau.medecin_id == medecin_id).all()
    return creneaux

@app.get("/api/rendez-vous/patient/{patient_id}", response_model=List[schemas.RendezVousResponse])
def get_rdv_patient(patient_id: int, db: Session = Depends(get_db)):
    rdvs = db.query(models.RendezVous).filter(models.RendezVous.patient_id == patient_id).all()
    return rdvs