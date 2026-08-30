import uuid
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

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

@app.get("/")
def read_root():
    return {"status": "API SantéApp opérationnelle"}

@app.post("/api/auth/register")
def register(user_data: schemas.UserRegister, db: Session = Depends(get_db)):
    try:
        existing_user = db.query(models.User).filter(models.User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Cet email est déjà utilisé.")

        hashed_pwd = security.get_password_hash(user_data.password)
        nid_genere = f"NID-{uuid.uuid4().hex[:6].upper()}" if user_data.role == "Patient" else None

        new_user = models.User(
            nom=user_data.nom,
            prenom=user_data.prenom,
            email=user_data.email,
            password_hash=hashed_pwd,
            role=user_data.role,
            lieu_exercice=getattr(user_data, 'lieu_exercice', None),
            carte_digitale_id=nid_genere,
            groupe_sanguin=getattr(user_data, 'groupe_sanguin', None),
            allergies=getattr(user_data, 'allergies', None),
            antecedents=getattr(user_data, 'antecedents', None)
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return {"message": "Compte créé avec succès", "user_id": new_user.id}

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        db.rollback()
        print(f"Erreur d'inscription : {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur serveur : {str(e)}")

@app.post("/api/auth/login")
def login(user_credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == user_credentials.email).first()
    if not user or not security.verify_password(user_credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect.")

    access_token = security.create_access_token(data={"sub": str(user.id), "role": user.role})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "nom": user.nom,
            "prenom": user.prenom,
            "email": user.email,
            "role": user.role,
            "carte_digitale_id": user.carte_digitale_id
        }
    }