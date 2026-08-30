from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
from database import engine, get_db, Base
import models
import schemas
import security

Base.metadata.create_all(bind=engine)

app = FastAPI(title="SantéApp Backend API", version="1.0.0")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root():
    return FileResponse("static/index.html")

# --- AUTHENTIFICATION ---

@app.post("/api/auth/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un compte existe déjà avec cette adresse email."
        )

    hashed_pwd = security.get_password_hash(user_data.password)
    new_user = models.User(
        nom=user_data.nom,
        prenom=user_data.prenom,
        email=user_data.email,
        hashed_password=hashed_pwd,
        role=user_data.role.upper(),
        specialite=user_data.specialite if user_data.role.upper() == "MEDECIN" else None
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.post("/api/auth/login", response_model=schemas.Token)
def login(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == credentials.email).first()
    if not user or not security.verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect."
        )

    access_token = security.create_access_token(data={"sub": user.email})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "nom": user.nom,
        "prenom": user.prenom
    }


@app.post("/api/auth/forgot-password")
def forgot_password(payload: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user:
        return {"message": "Si l'adresse email existe, un lien de réinitialisation a été généré."}
    
    reset_token = security.create_reset_password_token(user.email)
    print(f"\n[RESET PASSWORD KEY] Token généré pour {user.email} : {reset_token}\n")
    return {"message": "Si l'adresse email existe, un lien de réinitialisation a été généré."}


@app.post("/api/auth/reset-password")
def reset_password(payload: schemas.ResetPasswordConfirm, db: Session = Depends(get_db)):
    email = security.verify_reset_password_token(payload.token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le jeton de réinitialisation est invalide ou a expiré."
        )
    
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé."
        )
    
    user.hashed_password = security.get_password_hash(payload.new_password)
    db.commit()
    return {"message": "Le mot de passe a été réinitialisé avec succès."}


# --- GESTION DES CRÉNEAUX HORAIRES ---

@app.post("/api/creneaux", response_model=schemas.CreneauResponse, status_code=status.HTTP_201_CREATED)
def create_creneau(
    creneau_data: schemas.CreneauCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    if current_user.role != "MEDECIN":
        raise HTTPException(status_code=403, detail="Seuls les médecins peuvent ajouter des créneaux.")
    
    if creneau_data.date_heure_fin <= creneau_data.date_heure_debut:
        raise HTTPException(status_code=400, detail="La date de fin doit être supérieure à la date de début.")

    new_creneau = models.Creneau(
        medecin_id=current_user.id,
        date_heure_debut=creneau_data.date_heure_debut,
        date_heure_fin=creneau_data.date_heure_fin,
        est_disponible=True
    )
    db.add(new_creneau)
    db.commit()
    db.refresh(new_creneau)
    return new_creneau


@app.get("/api/medecins/{medecin_id}/creneaux", response_model=List[schemas.CreneauResponse])
def get_medecin_creneaux(medecin_id: int, db: Session = Depends(get_db)):
    return db.query(models.Creneau).filter(
        models.Creneau.medecin_id == medecin_id,
        models.Creneau.est_disponible == True
    ).all()


@app.get("/api/medecins", response_model=List[schemas.UserResponse])
def get_medecins(db: Session = Depends(get_db)):
    return db.query(models.User).filter(models.User.role == "MEDECIN").all()