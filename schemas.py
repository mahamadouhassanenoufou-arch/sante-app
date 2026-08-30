from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# --- AUTHENTIFICATION & MOT DE PASSE ---
class UserLogin(BaseModel):
    email: EmailStr
    password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordConfirm(BaseModel):
    token: str
    new_password: str

ResetPasswordRequest = ResetPasswordConfirm

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None

# --- UTILISATEUR / MEDECIN ---
class UserBase(BaseModel):
    nom: str
    prenom: str
    email: EmailStr
    role: str
    specialite: Optional[str] = None
    hopital: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    class Config:
        from_attributes = True

# --- CRENEAUX ---
class CreneauBase(BaseModel):
    date_heure_debut: datetime
    date_heure_fin: datetime

class CreneauCreate(CreneauBase):
    pass

class CreneauResponse(CreneauBase):
    id: int
    medecin_id: int
    est_disponible: bool
    class Config:
        from_attributes = True

# --- DOSSIER MEDICAL DEFINITIF ---
class DossierMedicalBase(BaseModel):
    groupe_sanguin: Optional[str] = None
    antecedents: Optional[str] = None
    allergies: Optional[str] = None
    notes_medecin: Optional[str] = None

class DossierMedicalCreate(DossierMedicalBase):
    patient_id: int

class DossierMedicalResponse(DossierMedicalBase):
    id: int
    patient_id: int
    class Config:
        from_attributes = True

# --- RENDEZ-VOUS ---
class RendezVousBase(BaseModel):
    medecin_id: int
    creneau_id: Optional[int] = None
    hopital: Optional[str] = None
    motif: str
    symptomes: Optional[str] = None

class RendezVousCreate(RendezVousBase):
    pass

class RendezVousResponse(RendezVousBase):
    id: int
    patient_id: int
    statut: str
    diagnostic: Optional[str] = None
    prescription: Optional[str] = None
    class Config:
        from_attributes = True