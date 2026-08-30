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
        from_attributes = Truefrom pydantic import BaseModel
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
        orm_mode = True

class PatientCardOut(BaseModel):
    carte_digitale_id: str
    nom: str
    prenom: str
    groupe_sanguin: Optional[str]
    allergies: Optional[str]
    antecedents: Optional[str]
    historique: List[ConsultationOut] = []
    