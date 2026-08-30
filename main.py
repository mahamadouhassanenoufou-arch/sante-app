import os
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

import models, schemas, utils
from database import engine, get_db

# Création des tables dans la base de données PostgreSQL
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="SantéApp API")

# Configuration CORS pour autoriser le PWA frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service des fichiers statiques (Frontend HTML/CSS/JS)
# Assurez-vous que vos fichiers HTML (index.html, etc.) sont bien dans le dossier 'static'
app.mount("/static", StaticFiles(directory="static"), name="static")


# --- HELPER SMTP SÉCURISÉ ---
def send_email_safe(to_email: str, subject: str, content: str):
    mail_server = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    mail_port = int(os.getenv("MAIL_PORT", 587))
    mail_user = os.getenv("MAIL_USERNAME")
    mail_pass = os.getenv("MAIL_PASSWORD")

    if not mail_user or not mail_pass:
        print(" [SMTP WARN] Variables SMTP non définies. Mail ignoré.")
        return

    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = mail_user
        msg["To"] = to_email
        msg.set_content(content)

        with smtplib.SMTP(mail_server, mail_port, timeout=10) as server:
            server.starttls()
            server.login(mail_user, mail_pass)
            server.send_message(msg)
        print(f" [SMTP OK] Mail envoyé à {to_email}")
    except Exception as e:
        print(f" [SMTP ERROR] Échec d'envoi du mail : {e}")


# --- ROUTE RACINE (SERVEUR PWA FRONTEND) ---

@app.get("/")
def read_root():
    return FileResponse("static/index.html")


# --- ROUTES AUTHENTIFICATION ---

@app.post("/api/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
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

    # Envoi du mail de bienvenue sans bloquer l'inscription si SMTP échoue
    send_email_safe(
        to_email=new_user.email,
        subject="Bienvenue sur SantéApp",
        content=f"Bonjour {new_user.prenom},\n\nVotre compte a été créé avec succès."
    )

    return new_user


@app.post("/api/login", response_model=schemas.Token)
def login(user_credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == user_credentials.email).first()
    if not user or not utils.verify_password(user_credentials.password, user.password):
        raise HTTPException(status_code=401, detail="Identifiants incorrects.")

    access_token = utils.create_access_token(data={"sub": user.email, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/api/forgot-password")
def forgot_password(payload: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user:
        return {"message": "Si l'adresse existe, un e-mail de réinitialisation a été envoyé."}
    
    reset_token = utils.create_access_token(data={"sub": user.email}, expires_delta=timedelta(minutes=15))
    
    send_email_safe(
        to_email=user.email,
        subject="Réinitialisation de votre mot de passe",
        content=f"Bonjour,\n\nVoici votre jeton de réinitialisation : {reset_token}"
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


# --- ROUTES CRÉNEAUX ---

@app.post("/api/creneaux", response_model=schemas.CreneauResponse, status_code=status.HTTP_201_CREATED)
def create_creneau(creneau: schemas.CreneauCreate, db: Session = Depends(get_db)):
    new_creneau = models.Creneau(**creneau.dict())
    db.add(new_creneau)
    db.commit()
    db.refresh(new_creneau)
    return new_creneau


# --- ROUTES RENDEZ-VOUS ---

@app.post("/api/rendez-vous", response_model=schemas.RendezVousResponse, status_code=status.HTTP_201_CREATED)
def create_rendez_vous(rdv: schemas.RendezVousCreate, db: Session = Depends(get_db)):
    new_rdv = models.RendezVous(**rdv.dict(), statut="en_attente")
    db.add(new_rdv)
    db.commit()
    db.refresh(new_rdv)
    return new_rdv
# Route de secours si le JS frontend appelle /register sans le prefixe /api
@app.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register_alias(user: schemas.UserCreate, db: Session = Depends(get_db)):
    return register(user, db)