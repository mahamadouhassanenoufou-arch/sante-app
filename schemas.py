from pydantic import BaseModel, EmailStr
from typing import Optional, List

class UserCreate(BaseModel):
    nom: str
    prenom: str
    email: EmailStr
    password: str
    role: str
    specialite: Optional[str] = None
    hopital: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    nom: str
    prenom: str
    email: EmailStr
    role: str
    specialite: Optional[str] = None
    hopital: Optional[str] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    nom: str
    prenom: str
    role: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordConfirm(BaseModel):
    token: str
    new_password: str

class CreneauCreate(BaseModel):
    medecin_id: int
    date_heure: Optional[str] = None
    date_debut: Optional[str] = None
    date_fin: Optional[str] = None

class CreneauResponse(BaseModel):
    id: int
    medecin_id: int
    date_heure: Optional[str] = None
    date_debut: Optional[str] = None
    date_fin: Optional[str] = None

    class Config:
        from_attributes = True

class RendezVousCreate(BaseModel):
    patient_id: int
    creneau_id: int
    motif: Optional[str] = None

class RendezVousResponse(BaseModel):
    id: int
    patient_id: int
    creneau_id: int
    statut: str
    motif: Optional[str] = None

    class Config:
        from_attributes = True