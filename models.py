from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, nullable=False)
    prenom = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False)
    specialite = Column(String, nullable=True)
    hopital = Column(String, nullable=True)

class Creneau(Base):
    __tablename__ = "creneaux"

    id = Column(Integer, primary_key=True, index=True)
    medecin_id = Column(Integer, ForeignKey("users.id"))
    date_heure = Column(String, nullable=False)

class RendezVous(Base):
    __tablename__ = "rendez_vous"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"))
    creneau_id = Column(Integer, ForeignKey("creneaux.id"))
    statut = Column(String, default="en_attente")