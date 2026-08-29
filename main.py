import os
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

# Importation de vos modules locaux (adaptez selon votre structure réelle)
from database import get_db, engine
import models

# Initialisation de l'application FastAPI
app = FastAPI(
    title="Santé App API",
    version="2.0",
    description="API de gestion médicale et PWA pour Patients et Médecins"
)

# --- 1. Configuration CORS (pour accès mobile et externe) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production si nécessaire
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. Configuration des Fichiers Statiques et PWA ---
# S'assure que le dossier 'static' existe pour éviter des erreurs au démarrage
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=FileResponse)
async def serve_index():
    """Sert l'interface utilisateur PWA principale."""
    index_path = os.path.join("static", "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="Fichier index.html introuvable dans static/")
    return FileResponse(index_path)

@app.get("/manifest.json", response_class=FileResponse)
async def serve_manifest():
    """Sert le fichier de configuration PWA."""
    return FileResponse(os.path.join("static", "manifest.json"))

@app.get("/sw.js", response_class=FileResponse)
async def serve_sw():
    """Sert le Service Worker pour le fonctionnement hors-ligne."""
    return FileResponse(os.path.join("static", "sw.js"))

# --- 3. Verification de Santé (Health Check) ---
@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur DB: {str(e)}")

# --- 4. Endpoints d'Exemple pour la PWA (Patients & Médecins) ---
@app.post("/api/data")
async def receive_data(payload: dict, db: Session = Depends(get_db)):
    """
    Endpoint de réception des formulaires envoyés depuis la PWA
    (Prend en charge la synchronisation des données hors-ligne).
    """
    print(f"Données reçues de la PWA: {payload}")
    # Insérez ici votre logique de sauvegarde en BDD avec vos modèles SQLAlchemy
    return {"status": "success", "message": "Données enregistrées avec succès"}

@app.get("/api/patient/dashboard")
async def get_patient_dashboard(db: Session = Depends(get_db)):
    """Données spécifiques à l'espace Patient."""
    return {
        "role": "patient",
        "prochain_rdv": {"medecin": "Dr. Abdoulaye", "specialite": "Cardiologie", "date": "Demain à 09:30"}
    }

@app.get("/api/medecin/dashboard")
async def get_medecin_dashboard(db: Session = Depends(get_db)):
    """Données spécifiques à l'espace Médecin."""
    return {
        "role": "medecin",
        "consultations_du_jour": 8,
        "patients_en_attente": 2
    }