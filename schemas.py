from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class UserRegister(BaseModel):
    nom: str
    prenom: str
    email: str
    password: str
    role: str
    groupe_sanguin: Optional[str] = None
    allergies: Optional[str] = None
    antecedents: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class ConsultationCreate(BaseModel):
    carte_digitale_id: str
    symptomes: str
    diagnostic: str
    prescription: Optional[str] = None

class ConsultationOut(BaseModel):
    id: int
    date_consultation: datetime
    medecin_nom: str
    symptomes: str
    diagnostic: str
    prescription: Optional[str]

    class Config:
        from_attributes = True  # Pydantic v2 (ou orm_mode = True pour Pydantic v1)

class PatientCardOut(BaseModel):
    carte_digitale_id: str
    nom: str
    prenom: str
    groupe_sanguin: Optional[str]
    allergies: Optional[str]
    antecedents: Optional[str]
    historique: List[ConsultationOut] = []