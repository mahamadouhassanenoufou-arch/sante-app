from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt

import models
import schemas
import security
from database import get_db, engine

# Création automatique des tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Santé App API", version="2.0")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# --- Dépendance pour récupérer l'utilisateur connecté via JWT ---
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Identifiants invalides ou session expirée",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

# --- Endpoint Inscription ---
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
        role=user_in.role,
        telephone=user_in.telephone
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# --- Endpoint Connexion (génère le JWT) ---
@app.post("/api/auth/login", response_model=schemas.Token)
def login(user_credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == user_credentials.email).first()
    if not user or not security.verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect"
        )
    
    access_token = security.create_access_token(data={"sub": user.email, "role": user.role.value})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role.value,
        "nom": user.nom,
        "prenom": user.prenom
    }

# --- Endpoint Protegé de profil ---
@app.get("/api/auth/me", response_model=schemas.UserOut)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user