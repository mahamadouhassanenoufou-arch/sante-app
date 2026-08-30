from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import models, schemas, security
from database import engine, get_db
from sqlalchemy import text

# 1. Initialiser l'application FastAPI EN PREMIER
app = FastAPI(title="Santé App")

# 2. Monter les fichiers statiques (si applicable)
app.mount("/static", StaticFiles(directory="static"), name="static")

# 3. Synchronisation/Migration BDD au démarrage
try:
    models.Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS specialite VARCHAR;"))
        conn.execute(text("ALTER TABLE consultations ADD COLUMN IF NOT EXISTS rdv_id INTEGER REFERENCES rendez_vous(id);"))
        conn.execute(text("ALTER TABLE consultations ADD COLUMN IF NOT EXISTS prescription TEXT;"))
        conn.execute(text("ALTER TABLE consultations ADD COLUMN IF NOT EXISTS date TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"))
        conn.commit()
except Exception as e:
    print(f"Sync DB: {e}")

# 4. Route pour la page d'accueil
@app.get("/")
def read_index():
    from fastapi.responses import FileResponse
    return FileResponse("static/index.html")

# 5. Routes API
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

# Route mise à jour pour inclure la spécialité des médecins
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
    # Récupérer uniquement les RDV du patient connecté ou passer son ID
    # Exemple pour filtrer les RDV de l'utilisateur courant :
    patient = db.query(models.User).filter(models.User.role == "PATIENT").first()
    if not patient:
        return []
    
    # Pour un filtrage strict par patient connecté, adaptez la requête :
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