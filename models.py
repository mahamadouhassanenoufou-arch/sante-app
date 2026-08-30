import enum
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Enum, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class RoleEnum(str, enum.Enum):
    PATIENT = "PATIENT"
    MEDECIN = "MEDECIN"
    ADMIN = "ADMIN"

class StatutRDV(str, enum.Enum):
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
    role = Column(String, default="PATIENT")
    specialite = Column(String, nullable=True)

    rdvs_patient = relationship("RendezVous", foreign_keys="RendezVous.patient_id", back_populates="patient")
    rdvs_medecin = relationship("RendezVous", foreign_keys="RendezVous.medecin_id", back_populates="medecin")

class RendezVous(Base):
    __tablename__ = "rendez_vous"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    medecin_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    motif = Column(String, nullable=False)
    statut = Column(Enum(StatutRDV), default=StatutRDV.EN_ATTENTE)

    patient = relationship("User", foreign_keys=[patient_id], back_populates="rdvs_patient")
    medecin = relationship("User", foreign_keys=[medecin_id], back_populates="rdvs_medecin")
    consultation = relationship("Consultation", back_populates="rdv", uselist=False)

class Consultation(Base):
    __tablename__ = "consultations"

    id = Column(Integer, primary_key=True, index=True)
    rdv_id = Column(Integer, ForeignKey("rendez_vous.id"), nullable=False)
    symptomes = Column(Text, nullable=False)
    diagnostic = Column(Text, nullable=False)
    prescription = Column(Text, nullable=True)
    date = Column(DateTime(timezone=True), server_default=func.now())

    rdv = relationship("RendezVous", back_populates="consultation")