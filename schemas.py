from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

# --- Vos schémas existants ---
class UserCreate(BaseModel):
    nom: str
    prenom: str
    email: str
    password: str
    role: str = "PATIENT"

class UserOut(BaseModel):
    id: int
    nom: str
    prenom: str
    email: str
    role: str

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    nom: Optional[str] = None
    prenom: Optional[str] = None

# --- Nouveaux schémas Médecin ---
class RdvOut(BaseModel):
    id: int
    date_heure: datetime
    motif: str
    statut: str
    patient_id: int
    nom_patient: Optional[str] = None
    prenom_patient: Optional[str] = None

    class Config:
        from_attributes = True

class ConsultationCreate(BaseModel):
    rdv_id: int
    symptomes: str
    diagnostic: str
    prescription: str

class ConsultationOut(BaseModel):
    id: int
    symptomes: Optional[str] = None
    diagnostic: str
    prescription: Optional[str] = None
    rdv_id: int

    class Config:
        from_attributes = True