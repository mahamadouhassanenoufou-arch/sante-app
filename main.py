from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

import models, schemas, security
from database import engine, get_db

app = FastAPI(title="Santé App")

app.mount("/static", StaticFiles(directory="static"), name="static")

# Synchronisation sécurisée des tables et colonnes PostgreSQL
try:
    models.Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS specialite VARCHAR;"))
        conn.execute(text("ALTER TABLE consultations ADD COLUMN IF NOT EXISTS rdv_id INTEGER REFERENCES rendez_vous(id);"))
        conn.execute(text("ALTER TABLE consultations ADD COLUMN IF NOT EXISTS prescription TEXT;"))
        conn.execute(text("ALTER TABLE consultations ADD COLUMN IF NOT EXISTS date TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"))
        # Alignement pour la table rendez_vous
        conn.execute(text("ALTER TABLE rendez_vous ADD COLUMN IF NOT EXISTS date_heure TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"))
        conn.execute(text("ALTER TABLE rendez_vous ALTER COLUMN date_heure SET DEFAULT CURRENT_TIMESTAMP;"))
        conn.commit()
except Exception as e:
    print(f"Sync DB warning: {e}")

@app.get("/")
def read_index():
    return FileResponse("static/index.html")

# ----------------- AUTHENTIFICATION -----------------

@app.post("/api/auth/register", response_model=schemas.UserOut)
def register_user(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user_in.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Cet email est déjà enregistré.")
    
    hashed_pwd = security.get_password_hash(user_in.password)
    new_user = models.User(
        nom=user_in.nom,
        prenom=user_in.prenom,
        email=user_in.email,
        hashed_password=hashed_pwd,
        role=user_in.role.upper(),
        specialite=user_in.specialite if user_in.role.upper() == "MEDECIN" else None
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/api/auth/login")
def login(login_data: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == login_data.email).first()
    if not user or not security.verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Email ou mot de passe incorrect.")
    
    access_token = security.create_access_token(data={"sub": str(user.id), "role": user.role})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "role": user.role,
        "nom": user.nom,
        "prenom": user.prenom
    }

# ----------------- PATIENT -----------------

@app.get("/api/patient/medecins")
def get_list_medecins(db: Session = Depends(get_db)):
    medecins = db.query(models.User).filter(models.User.role == "MEDECIN").all()
    return [
        {
            "id": m.id, 
            "nom": m.nom, 
            "prenom": m.prenom,
            "specialite": m.specialite or "Généraliste"
        } 
        for m in medecins
    ]

@app.post("/api/patient/rdv")
def create_rdv(
    data: schemas.RdvCreate, 
    current_user: models.User = Depends(security.get_current_user), 
    db: Session = Depends(get_db)
):
    if current_user.role != "PATIENT":
        raise HTTPException(status_code=403, detail="Accès réservé aux patients.")
    
    medecin = db.query(models.User).filter(
        models.User.id == int(data.medecin_id), 
        models.User.role == "MEDECIN"
    ).first()
    
    if not medecin:
        raise HTTPException(status_code=404, detail="Le médecin sélectionné n'existe pas.")

    # Détermination sécurisée du statut
    statut_val = "EN_ATTENTE"
    if hasattr(models, "StatutRDV") and hasattr(models.StatutRDV, "EN_ATTENTE"):
        statut_val = models.StatutRDV.EN_ATTENTE.value if hasattr(models.StatutRDV.EN_ATTENTE, 'value') else "EN_ATTENTE"

    # Création directe sécurisée avec date_heure explicite
    new_rdv = models.RendezVous(
        patient_id=int(current_user.id),
        medecin_id=int(data.medecin_id),
        motif=data.motif,
        statut=statut_val,
        date_heure=datetime.utcnow()
    )

    try:
        db.add(new_rdv)
        db.commit()
        db.refresh(new_rdv)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur DB SQL: {str(e)}")

    return {"message": "Rendez-vous enregistré avec succès"}

@app.get("/api/patient/my-rdv")
def get_patient_rdvs(
    current_user: models.User = Depends(security.get_current_user), 
    db: Session = Depends(get_db)
):
    if current_user.role != "PATIENT":
        raise HTTPException(status_code=403, detail="Accès réservé aux patients.")
    
    rdvs = db.query(models.RendezVous).filter(models.RendezVous.patient_id == current_user.id).all()
    res = []
    for r in rdvs:
        c = db.query(models.Consultation).filter(models.Consultation.rdv_id == r.id).first()
        medecin = db.query(models.User).filter(models.User.id == r.medecin_id).first()
        
        statut_str = r.statut.value if hasattr(r.statut, 'value') else str(r.statut)
        
        res.append({
            "id": r.id,
            "medecin_nom": f"Dr. {medecin.prenom} {medecin.nom}" if medecin else "Praticien",
            "specialite": medecin.specialite if medecin and medecin.specialite else "Généraliste",
            "motif": r.motif,
            "statut": statut_str,
            "symptomes": c.symptomes if c else None,
            "diagnostic": c.diagnostic if c else None,
            "prescription": c.prescription if c else None
        })
    return res

# ----------------- MEDECIN -----------------

@app.get("/api/medecin/rdv")
def get_medecin_rdvs(
    current_user: models.User = Depends(security.get_current_user), 
    db: Session = Depends(get_db)
):
    if current_user.role != "MEDECIN":
        raise HTTPException(status_code=403, detail="Accès réservé aux médecins.")
    
    rdvs = db.query(models.RendezVous).filter(models.RendezVous.medecin_id == current_user.id).all()
    res = []
    for r in rdvs:
        patient = db.query(models.User).filter(models.User.id == r.patient_id).first()
        statut_str = r.statut.value if hasattr(r.statut, 'value') else str(r.statut)
        res.append({
            "id": r.id,
            "patient_id": r.patient_id,
            "nom_patient": patient.nom if patient else "Inconnu",
            "prenom_patient": patient.prenom if patient else "",
            "motif": r.motif,
            "statut": statut_str
        })
    return res

@app.post("/api/medecin/consultation")
def create_consultation(
    data: schemas.ConsultationCreate, 
    current_user: models.User = Depends(security.get_current_user), 
    db: Session = Depends(get_db)
):
    if current_user.role != "MEDECIN":
        raise HTTPException(status_code=403, detail="Accès réservé aux médecins.")
    
    rdv = db.query(models.RendezVous).filter(
        models.RendezVous.id == int(data.rdv_id), 
        models.RendezVous.medecin_id == current_user.id
    ).first()
    
    if not rdv:
        raise HTTPException(status_code=404, detail="Rendez-vous introuvable.")
    
    consult = models.Consultation(
        rdv_id=rdv.id,
        symptomes=data.symptomes,
        diagnostic=data.diagnostic,
        prescription=data.prescription
    )
    
    statut_done = "TERMINE"
    if hasattr(models, "StatutRDV") and hasattr(models.StatutRDV, "TERMINE"):
        statut_done = models.StatutRDV.TERMINE.value if hasattr(models.StatutRDV.TERMINE, 'value') else "TERMINE"
        
    rdv.statut = statut_done
    
    try:
        db.add(consult)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur enregistrement consultation : {str(e)}")

    return {"message": "Consultation enregistrée avec succès."}