from pydantic import BaseModel, EmailStr
from typing import Optional
from models import UserRole

# Inscription utilisateur
class UserCreate(BaseModel):
    nom: str
    prenom: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.PATIENT
    telephone: Optional[str] = None

# Connexion utilisateur
class UserLogin(BaseModel):
    email: EmailStr
    password: str

# Format de réponse Token JWT
class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    nom: str
    prenom: str

# Données retournées du profil
class UserOut(BaseModel):
    id: int
    nom: str
    prenom: str
    email: EmailStr
    role: UserRole
    telephone: Optional[str] = None

    class Config:
        from_attributes = True