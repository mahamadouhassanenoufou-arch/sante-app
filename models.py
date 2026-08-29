import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from database import Base

class RoleEnum(str, enum.Enum):
    PATIENT = "PATIENT"
    MEDECIN = "MEDECIN"

class StatusRdv(str, enum.Enum):
    EN_ATTENTE = "EN_ATTENTE"
    CONFIRME = "CONFIRME"
    TERMINE = "TERMINE"
    ANNULE = "ANNULE"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, nullable=False)
    prenom = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(SQLEnum(RoleEnum), default=RoleEnum.PATIENT)
    telephone = Column(String, nullable=True)

class RendezVous(Base):
    __tablename__ = "rendez_vous"

    id = Column(Integer, primary_key=True, index=True)
    date_heure = Column(DateTime, default=datetime.utcnow)
    motif = Column(String, nullable=False)
    statut = Column(SQLEnum(StatusRdv), default=StatusRdv.EN_ATTENTE)

    patient_id = Column(Integer, ForeignKey("users.id"))
    medecin_id = Column(Integer, ForeignKey("users.id"))

    patient = relationship("User", foreign_keys=[patient_id])
    medecin = relationship("User", foreign_keys=[medecin_id])
    consultation = relationship("Consultation", back_populates="rdv", uselist=False)

class Consultation(Base):
    __tablename__ = "consultations"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.utcnow)
    symptomes = Column(Text, nullable=True)
    diagnostic = Column(Text, nullable=False)
    prescription = Column(Text, nullable=True)

    rdv_id = Column(Integer, ForeignKey("rendez_vous.id"))
    rdv = relationship("RendezVous", back_populates="consultation")