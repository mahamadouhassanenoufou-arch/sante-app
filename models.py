import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

# Enums pour fixer la gestion des rôles et des statuts de rendez-vous
class UserRole(str, enum.Enum):
    PATIENT = "PATIENT"
    MEDECIN = "MEDECIN"
    ADMIN = "ADMIN"

class StatutRDV(str, enum.Enum):
    EN_ATTENTE = "EN_ATTENTE"
    CONFIRME = "CONFIRME"
    ANNULE = "ANNULE"
    TERMINE = "TERMINE"

# 1. Modèle Utilisateur / Profil
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(100), nullable=False)
    prenom = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.PATIENT, nullable=False)
    telephone = Column(String(20), nullable=True)
    
    # Informations spécifiques au patient
    groupe_sanguin = Column(String(5), nullable=True)
    antecedents = Column(Text, nullable=True)

    # Relations SQLAlchemy
    rendez_vous_patient = relationship("RendezVous", foreign_keys="RendezVous.patient_id", back_populates="patient")
    rendez_vous_medecin = relationship("RendezVous", foreign_keys="RendezVous.medecin_id", back_populates="medecin")
    consultations_recues = relationship("Consultation", foreign_keys="Consultation.patient_id", back_populates="patient")
    consultations_donnees = relationship("Consultation", foreign_keys="Consultation.medecin_id", back_populates="medecin")

# 2. Modèle Rendez-vous
class RendezVous(Base):
    __tablename__ = "rendez_vous"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    medecin_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date_heure = Column(DateTime(timezone=True), nullable=False)
    motif = Column(String(255), nullable=True)
    statut = Column(Enum(StatutRDV), default=StatutRDV.EN_ATTENTE, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    patient = relationship("User", foreign_keys=[patient_id], back_populates="rendez_vous_patient")
    medecin = relationship("User", foreign_keys=[medecin_id], back_populates="rendez_vous_medecin")

# 3. Modèle Consultation
class Consultation(Base):
    __tablename__ = "consultations"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    medecin_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symptomes = Column(Text, nullable=True)
    diagnostic = Column(Text, nullable=False)
    notes_privees = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    patient = relationship("User", foreign_keys=[patient_id], back_populates="consultations_recues")
    medecin = relationship("User", foreign_keys=[medecin_id], back_populates="consultations_donnees")
    ordonnance = relationship("Ordonnance", back_populates="consultation", uselist=False)

# 4. Modèle Ordonnance
class Ordonnance(Base):
    __tablename__ = "ordonnances"

    id = Column(Integer, primary_key=True, index=True)
    consultation_id = Column(Integer, ForeignKey("consultations.id"), nullable=False)
    contenu_medicaments = Column(Text, nullable=False) # Liste des médicaments et posologies
    instructions = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    consultation = relationship("Consultation", back_populates="ordonnance")