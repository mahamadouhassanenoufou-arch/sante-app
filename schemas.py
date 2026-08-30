from typing import Optional, List
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    nom: str
    prenom: str
    email: str
    password: str
    role: str = "PATIENT"
    specialite: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class UserOut(BaseModel):
    id: int
    nom: str
    prenom: str
    email: str
    role: str
    specialite: Optional[str] = None

    class Config:
        from_attributes = True

class RdvCreate(BaseModel):
    medecin_id: int
    motif: str

class ConsultationCreate(BaseModel):
    rdv_id: int
    symptomes: str
    diagnostic: str
    prescription: Optional[str] = None