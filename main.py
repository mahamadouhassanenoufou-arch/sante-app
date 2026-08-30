import uuid
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime

import models
import schemas
import security
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="SantéApp API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root():
    return FileResponse("static/index.html")

# --- AUTHENTIFICATION ---

@app.post("/api/auth/register")
def register(user_data: schemas.UserRegister, db: Session = Depends(get_db)):
    try:
        existing_user = db.query(models.User).filter(models.User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Cet email est déjà utilisé.")

        hashed_pwd = security.get_password_hash(user_data.password)
        nid_genere = f"NID-{uuid.uuid4().hex[:6].upper()}" if user_data.role.upper() == "PATIENT" else None

        new_user = models.User(
            nom=user_data.nom,
            prenom=user_data.prenom,
            email=user_data.email,
            password=hashed_pwd,  # Mappé sur la colonne 'password'
            role=user_data.role.upper(),
            lieu_exercice=user_data.lieu_exercice,
            carte_digitale_id=nid_genere,
            groupe_sanguin=user_data.groupe_sanguin,
            allergies=user_data.allergies,
            antecedents=user_data.antecedents
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return {"message": "Compte créé avec succès", "user_id": new_user.id}

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        db.rollback()
        print(f"Erreur inscription: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur base de données: {str(e)}")

@app.post("/api/auth/login")
def login(user_credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == user_credentials.email).first()
    if not user or not security.verify_password(user_credentials.password, user.password):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect.")

    access_token = security.create_access_token(data={"sub": str(user.id), "role": user.role})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "nom": user.nom,
        "prenom": user.prenom,
        "email": user.email,
        "role": user.role,
        "carte_digitale_id": user.carte_digitale_id,
        "groupe_sanguin": user.groupe_sanguin,
        "allergies": user.allergies,
        "antecedents": user.antecedents
    }

# --- CARTES & CONSULTATIONS ---

@app.get("/api/patient/scan/{carte_id}")
def scanner_carte(carte_id: str, db: Session = Depends(get_db)):
    patient = db.query(models.User).filter(models.User.carte_digitale_id == carte_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Carte non trouvée")
    
    historique = []
    for c in patient.consultations_recues:
        historique.append({
            "id": c.id,
            "date_consultation": c.date_consultation,
            "medecin_nom": f"Dr. {c.medecin.prenom} {c.medecin.nom}",
            "symptomes": c.symptomes,
            "diagnostic": c.diagnostic,
            "prescription": c.prescription
        })

    return {
        "carte_digitale_id": patient.carte_digitale_id,
        "nom": patient.nom,
        "prenom": patient.prenom,
        "groupe_sanguin": patient.groupe_sanguin,
        "allergies": patient.allergies,
        "antecedents": patient.antecedents,
        "historique": historique
    }

# --- RENDEZ-VOUS ---

@app.post("/api/rdv/creer")
def prendre_rdv(patient_id: int, medecin_id: int, date_heure: datetime, db: Session = Depends(get_db)):
    rdv_existant = db.query(models.RendezVous).filter(
        models.RendezVous.medecin_id == medecin_id,
        models.RendezVous.date_heure == date_heure,
        models.RendezVous.statut == "CONFIRME"
    ).first()

    if rdv_existant:
        raise HTTPException(status_code=400, detail="Créneau déjà réservé pour ce médecin.")

    medecin = db.query(models.User).filter(models.User.id == medecin_id).first()
    if not medecin:
        raise HTTPException(status_code=404, detail="Médecin introuvable")

    lieu = medecin.lieu_exercice or "Cabinet principal"

    nouveau_rdv = models.RendezVous(
        patient_id=patient_id,
        medecin_id=medecin_id,
        lieu=lieu,
        date_heure=date_heure,
        statut="CONFIRME"
    )

    db.add(nouveau_rdv)
    db.commit()
    return {"message": "Rendez-vous confirmé", "lieu": lieu, "date_heure": date_heure}

@app.get("/api/medecins/liste")
def lister_medecins(db: Session = Depends(get_db)):
    medecins = db.query(models.User).filter(models.User.role == "MEDECIN").all()
    return [
        {
            "id": m.id,
            "nom": f"Dr. {m.prenom} {m.nom}",
            "lieu": m.lieu_exercice or "Non renseigné"
        }
        for m in medecins
    ]