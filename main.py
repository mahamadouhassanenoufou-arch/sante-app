import os
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType

from database import engine, get_db
import models

# Monter le dossier static
app.mount("/static", StaticFiles(directory="static"), name="static")

# Rediriger la racine '/' et la route '/app' vers index.html
@app.get("/")
@app.get("/app")
def read_index():
    return FileResponse("static/index.html")
# ----------------------------------------------------
# 1. Configuration Sécurité & JWT
# ----------------------------------------------------
SECRET_KEY = "votre_cle_secrete_tres_securisee_ici"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# ----------------------------------------------------
# 2. Configuration FastAPI-Mail (SMTP)
# ----------------------------------------------------
# Vous pouvez configurer ici vos identifiants SMTP (ex: Gmail, Mailtrap, SendGrid, etc.)
# Pour des tests locaux sans bloquer, SUPPRESS_SEND=True évite d'échouer si le serveur SMTP n'est pas configuré.
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME", "votre_email@gmail.com"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD", "votre_mot_de_passe_app"),
    MAIL_FROM=os.getenv("MAIL_FROM", "noreply@santeapp.com"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
    MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
    SUPPRESS_SEND=1  # Mettre à 0 une fois vos vrais identifiants SMTP configurés
)

fastmail = FastMail(conf)

# Fonction d'envoi d'email
async def send_email_notification(email_to: str, subject: str, body: str):
    message = MessageSchema(
        subject=subject,
        recipients=[email_to],
        body=body,
        subtype=MessageType.html
    )
    await fastmail.send_message(message)

# ----------------------------------------------------
# 3. Schemas Pydantic
# ----------------------------------------------------
class UserCreate(BaseModel):
    nom: str
    prenom: str
    email: str
    password: str
    role: Optional[str] = "patient"

class UserOut(BaseModel):
    id: int
    nom: str
    prenom: str
    email: str
    role: str
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class MedecinCreate(BaseModel):
    nom: str
    prenom: str
    specialite: str
    email: str

class MedecinOut(BaseModel):
    id: int
    nom: str
    prenom: str
    specialite: str
    email: str
    class Config:
        from_attributes = True

class DisponibiliteCreate(BaseModel):
    jour_semaine: str
    heure_debut: str
    heure_fin: str

class DisponibiliteOut(BaseModel):
    id: int
    medecin_id: int
    jour_semaine: str
    heure_debut: str
    heure_fin: str
    class Config:
        from_attributes = True

class RendezVousCreate(BaseModel):
    medecin_id: int
    date_heure: datetime
    motif: str

class RendezVousOut(BaseModel):
    id: int
    patient_id: int
    medecin_id: int
    date_heure: datetime
    motif: str
    statut: str
    class Config:
        from_attributes = True

class NoteConsultationCreate(BaseModel):
    rendez_vous_id: int
    diagnostic: str
    prescription: Optional[str] = None

class NoteConsultationOut(BaseModel):
    id: int
    rendez_vous_id: int
    diagnostic: str
    prescription: Optional[str] = None
    date_creation: datetime
    class Config:
        from_attributes = True

# ----------------------------------------------------
# 4. Helper Functions
# ----------------------------------------------------
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Impossible de valider les identifiants",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

def require_role(roles: List[str]):
    def role_checker(current_user: models.User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous n'avez pas les permissions nécessaires"
            )
        return current_user
    return role_checker

# ----------------------------------------------------
# 5. Application FastAPI & Routes
# ----------------------------------------------------
app = FastAPI(title="Santé App API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/app")
def read_index():
    return FileResponse("static/index.html")

@app.post("/register", response_model=UserOut)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email déjà enregistré")
    hashed_pwd = get_password_hash(user.password)
    new_user = models.User(
        nom=user.nom,
        prenom=user.prenom,
        email=user.email,
        hashed_password=hashed_pwd,
        role=user.role or "patient"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/me", response_model=UserOut)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user

# --- MÉDECINS ---
@app.get("/medecins/", response_model=List[MedecinOut])
def list_medecins(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.Medecin).all()

@app.post("/medecins/", response_model=MedecinOut)
def create_medecin(medecin: MedecinCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_role(["admin"]))):
    new_med = models.Medecin(**medecin.dict())
    db.add(new_med)
    db.commit()
    db.refresh(new_med)
    return new_med

# --- DISPONIBILITÉS ---
@app.post("/medecins/{medecin_id}/disponibilites", response_model=DisponibiliteOut)
def add_disponibilite(medecin_id: int, dispo: DisponibiliteCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_role(["admin", "medecin"]))):
    medecin = db.query(models.Medecin).filter(models.Medecin.id == medecin_id).first()
    if not medecin:
        raise HTTPException(status_code=404, detail="Médecin non trouvé")
    new_dispo = models.Disponibilite(medecin_id=medecin_id, **dispo.dict())
    db.add(new_dispo)
    db.commit()
    db.refresh(new_dispo)
    return new_dispo

@app.get("/medecins/{medecin_id}/disponibilites", response_model=List[DisponibiliteOut])
def get_disponibilites(medecin_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.Disponibilite).filter(models.Disponibilite.medecin_id == medecin_id).all()

# --- RENDEZ-VOUS AVEC NOTIFICATION EMAIL ---
@app.post("/rendez-vous/", response_model=RendezVousOut)
def create_rendez_vous(
    rdv: RendezVousCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["patient", "admin"]))
):
    medecin = db.query(models.Medecin).filter(models.Medecin.id == rdv.medecin_id).first()
    if not medecin:
        raise HTTPException(status_code=404, detail="Médecin non trouvé")
    
    new_rdv = models.RendezVous(
        patient_id=current_user.id,
        medecin_id=rdv.medecin_id,
        date_heure=rdv.date_heure,
        motif=rdv.motif,
        statut="Confirmé"
    )
    db.add(new_rdv)
    db.commit()
    db.refresh(new_rdv)

    # Contenu de l'email de confirmation
    email_body = f"""
    <h2>Confirmation de votre rendez-vous</h2>
    <p>Bonjour {current_user.prenom} {current_user.nom},</p>
    <p>Votre rendez-vous avec le <strong>Dr. {medecin.prenom} {medecin.nom}</strong> est confirmé pour le :</p>
    <p><strong>{rdv.date_heure.strftime('%d/%m/%Y à %H:%M')}</strong></p>
    <p>Motif : {rdv.motif}</p>
    <br>
    <p>Merci de faire confiance à Santé App.</p>
    """

    # Envoi en tâche de fond (Background Task)
    background_tasks.add_task(
        send_email_notification,
        email_to=current_user.email,
        subject="Confirmation de votre rendez-vous - Santé App",
        body=email_body
    )

    return new_rdv

@app.get("/rendez-vous/mes-rdv", response_model=List[RendezVousOut])
def get_my_rendez_vous(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role == "medecin":
        medecin = db.query(models.Medecin).filter(models.Medecin.email == current_user.email).first()
        if not medecin:
            return []
        return db.query(models.RendezVous).filter(models.RendezVous.medecin_id == medecin.id).all()
    else:
        return db.query(models.RendezVous).filter(models.RendezVous.patient_id == current_user.id).all()

# --- NOTES DE CONSULTATION ---
@app.post("/consultations/notes", response_model=NoteConsultationOut)
def create_note_consultation(
    note: NoteConsultationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(["medecin", "admin"]))
):
    rdv = db.query(models.RendezVous).filter(models.RendezVous.id == note.rendez_vous_id).first()
    if not rdv:
        raise HTTPException(status_code=404, detail="Rendez-vous non trouvé")
    
    rdv.statut = "Terminé"
    
    new_note = models.NoteConsultation(**note.dict())
    db.add(new_note)
    db.commit()
    db.refresh(new_note)
    return new_note

@app.get("/rendez-vous/{rendez_vous_id}/notes", response_model=List[NoteConsultationOut])
def get_notes_for_rdv(rendez_vous_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.NoteConsultation).filter(models.NoteConsultation.rendez_vous_id == rendez_vous_id).all()