from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import uuid
from typing import List

import models, schemas, utils
from database import engine, get_db

# Création automatique des tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI (title="SantéApp - Carte Digitale PWA")

# Fichiers statiques (PWA)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root():
    return FileResponse("static/index.html")

# ==========================================
# AUTHENTIFICATION & CARTE DIGITALE
# ==========================================

import uuid

@app.post("/api/auth/register")
def register(user_data: schemas.UserRegister, db: Session = Depends(get_db)):
    # Vérification si l'email existe déjà
    existing_user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Cet email est déjà utilisé.")

    # Hachage du mot de passe
    hashed_pwd = security.get_password_hash(user_data.password)

    # Génération automatique du NID pour la carte digitale
    nid_genere = f"NID-{uuid.uuid4().hex[:6].upper()}"

    # Création de l'objet User avec gestion des valeurs Optionnelles/None
    new_user = models.User(
        nom=user_data.nom,
        prenom=user_data.prenom,
        email=user_data.email,
        password_hash=hashed_pwd,
        role=user_data.role,
        lieu_exercice=getattr(user_data, 'lieu_exercice', None),
        carte_digitale_id=nid_genere if user_data.role == "Patient" else None,
        groupe_sanguin=user_data.groupe_sanguin,
        allergies=user_data.allergies,
        antecedents=user_data.antecedents
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "Compte créé avec succès", "user_id": new_user.id}

@app.post("/api/auth/login")
def login(user_data: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if not user or not utils.verify_password(user_data.password, user.password):
        raise HTTPException(status_code=400, detail="Identifiants incorrects")

    # Génération NID de secours si absent
    if not user.carte_digitale_id:
        user.carte_digitale_id = f"NID-{uuid.uuid4().hex[:8].upper()}"
        db.commit()

    return {
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

# ==========================================
# ACCÈS SCANNER MÉDECIN & HISTORIQUE PATIENT
# ==========================================

@app.get("/api/patient/scan/{carte_id}", response_model=schemas.PatientCardOut)
def scan_carte_patient(carte_id: str, db: Session = Depends(get_db)):
    """
    Appelé par le médecin lorsqu'il scanne le QR code 
    ou saisit l'ID de la carte du patient.
    """
    patient = db.query(models.User).filter(models.User.carte_digitale_id == carte_id).first()
    if not patient:
        raise HTTPException(status_code=440, detail="Carte non trouvée ou invalide")

    # Récupération de l'historique des consultations du patient
    consultations_db = db.query(models.Consultation).filter(models.Consultation.patient_id == patient.id).order_by(models.Consultation.date_consultation.desc()).all()

    historique = []
    for c in consultations_db:
        medecin = db.query(models.User).filter(models.User.id == c.medecin_id).first()
        medecin_name = f"Dr. {medecin.prenom} {medecin.nom}" if medecin else "Praticien inconnu"
        historique.append(schemas.ConsultationOut(
            id=c.id,
            date_consultation=c.date_consultation,
            medecin_nom=medecin_name,
            symptomes=c.symptomes,
            diagnostic=c.diagnostic,
            prescription=c.prescription
        ))

    return schemas.PatientCardOut(
        carte_digitale_id=patient.carte_digitale_id,
        nom=patient.nom,
        prenom=patient.prenom,
        groupe_sanguin=patient.groupe_sanguin,
        allergies=patient.allergies,
        antecedents=patient.antecedents,
        historique=historique
    )


@app.post("/api/consultations/create")
def create_consultation(data: schemas.ConsultationCreate, medecin_id: int, db: Session = Depends(get_db)):
    """
    Permet au médecin d'ajouter une consultation au dossier du patient 
    scanné grâce à sa carte.
    """
    patient = db.query(models.User).filter(models.User.carte_digitale_id == data.carte_digitale_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient introuvable avec ce NID")

    nouvelle_consultation = models.Consultation(
        patient_id=patient.id,
        medecin_id=medecin_id,
        symptomes=data.symptomes,
        diagnostic=data.diagnostic,
        prescription=data.prescription
    )

    db.add(nouvelle_consultation)
    db.commit()
    db.refresh(nouvelle_consultation)

    return {"message": "Consultation enregistrée avec succès sur la carte du patient."}

# Route pour réserver un rendez-vous (vérifie la disponibilité du médecin)
@app.post("/api/rdv/creer")
def prendre_rdv(patient_id: int, medecin_id: int, date_heure: datetime, db: Session = Depends(get_db)):
    # 1. Vérifier si le médecin a déjà un RDV à cette exacte heure
    rdv_existant = db.query(models.RendezVous).filter(
        models.RendezVous.medecin_id == medecin_id,
        models.RendezVous.date_heure == date_heure,
        models.RendezVous.statut == "CONFIRME"
    ).first()

    if rdv_existant:
        raise HTTPException(
            status_code=400, 
            detail="Ce créneau est déjà réservé pour ce médecin. Veuillez choisir une autre heure."
        )

    # 2. Récupérer le lieu du médecin
    medecin = db.query(models.User).filter(models.User.id == medecin_id).first()
    if not medecin:
        raise HTTPException(status_code=444, detail="Médecin introuvable")

    lieu = medecin.lieu_consultation or "Cabinet principal"

    # 3. Enregistrer le RDV
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


# Route pour lister les médecins et leurs lieux d'exercice
@app.get("/api/medecins/liste")
def lister_medecins(db: Session = Depends(get_db)):
    medecins = db.query(models.User).filter(models.User.role == "MEDECIN").all()
    return [
        {
            "id": m.id,
            "nom": f"Dr. {m.prenom} {m.nom}",
            "lieu": m.lieu_consultation or "Non renseigné"
        }
        for m in medecins
    ]