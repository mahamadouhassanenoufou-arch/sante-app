import os
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

# Modules locaux
import models
import schemas
import security
from database import get_db, engine

# Création automatique des tables dans PostgreSQL au démarrage
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Santé App API",
    version="2.0",
    description="Backend FastAPI & PWA pour l'application Santé App"
)

# --- 1. Middleware CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. Servir l'interface PWA & Fichiers Statiques ---
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=FileResponse)
async def serve_index():
    """Sert l'interface HTML principale."""
    index_path = os.path.join("static", "index.html") if os.path.exists("static/index.html") else "index.html"
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="Page introuvable")
    return FileResponse(index_path)

@app.get("/manifest.json", response_class=FileResponse)
async def serve_manifest():
    """Sert le fichier manifest PWA."""
    manifest_path = os.path.join("static", "manifest.json") if os.path.exists("static/manifest.json") else "manifest.json"
    return FileResponse(manifest_path)

@app.get("/sw.js", response_class=FileResponse)
async def serve_sw():
    """Sert le Service Worker."""
    sw_path = os.path.join("static", "sw.js") if os.path.exists("static/sw.js") else "sw.js"
    return FileResponse(sw_path)

# --- 3. Endpoints d'Authentification (JWT) ---
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

# --- 4. Health Check ---
@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur DB: {str(e)}")