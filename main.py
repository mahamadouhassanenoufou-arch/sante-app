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

# Auto-migration des tables
try:
    models.Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE consultations ADD COLUMN IF NOT EXISTS rdv_id INTEGER REFERENCES rendez_vous(id);"))
        conn.execute(text("ALTER TABLE consultations ADD COLUMN IF NOT EXISTS prescription TEXT;"))
        conn.execute(text("ALTER TABLE consultations ADD COLUMN IF NOT EXISTS date TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"))
        conn.commit()
except Exception as e:
    print(f"Sync DB: {e}")

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

@app.post("/api/auth/login", response_model=schemas.Token)
def login(user_credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == user_credentials.email).first()
    if not user or not security.verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    
    # Extraction propre de la valeur du role
    user_role = user.role.value if hasattr(user.role, 'value') else str(user.role)
    user_role = user_role.upper()

    access_token = security.create_access_token(data={"sub": user.email, "role": user_role})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user_role,
        "nom": user.nom,
        "prenom": user.prenom
    }

# --- ROUTES PATIENT ---

@app.get("/api/patient/medecins")
def get_list_medecins(db: Session = Depends(get_db)):
    medecins = db.query(models.User).filter(models.User.role == "MEDECIN").all()
    return [{"id": m.id, "nom": m.nom, "prenom": m.prenom} for m in medecins]

@app.post("/api/patient/rdv")
def create_rdv(data: schemas.RdvCreate, db: Session = Depends(get_db)):
    patient = db.query(models.User).filter(models.User.role == "PATIENT").first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient non trouve")
    
    new_rdv = models.RendezVous(
        motif=data.motif,
        patient_id=patient.id,
        medecin_id=data.medecin_id,
        statut="EN_ATTENTE"
    )
    db.add(new_rdv)
    db.commit()
    db.refresh(new_rdv)
    return {"message": "Rendez-vous créé avec succès !"}

@app.get("/api/patient/my-rdv")
def get_patient_rdvs(db: Session = Depends(get_db)):
    patient = db.query(models.User).filter(models.User.role == "PATIENT").first()
    if not patient:
        return []
    rdvs = db.query(models.RendezVous).filter(models.RendezVous.patient_id == patient.id).all()
    
    res = []
    for r in rdvs:
        c = db.query(models.Consultation).filter(models.Consultation.rdv_id == r.id).first()
        res.append({
            "id": r.id,
            "motif": r.motif,
            "statut": str(r.statut.value) if hasattr(r.statut, 'value') else str(r.statut),
            "symptomes": c.symptomes if c else None,
            "diagnostic": c.diagnostic if c else None,
            "prescription": c.prescription if c else None
        })
    return res

# --- ROUTES MEDECIN ---

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