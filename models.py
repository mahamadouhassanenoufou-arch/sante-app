from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, nullable=False)
    prenom = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    
    lieu_exercice = Column(String, nullable=True)
    carte_digitale_id = Column(String, unique=True, index=True, nullable=True)
    groupe_sanguin = Column(String, nullable=True)
    allergies = Column(Text, nullable=True)
    antecedents = Column(Text, nullable=True)

    consultations_recues = relationship("Consultation", foreign_keys="Consultation.patient_id", back_populates="patient")
    consultations_donnees = relationship("Consultation", foreign_keys="Consultation.medecin_id", back_populates="medecin")
    rdv_patients = relationship("RendezVous", foreign_keys="RendezVous.patient_id", back_populates="patient")
    rdv_medecins = relationship("RendezVous", foreign_keys="RendezVous.medecin_id", back_populates="medecin")


class RendezVous(Base):
    __tablename__ = "rendez_vous"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    medecin_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lieu = Column(String, nullable=False)
    date_heure = Column(DateTime, nullable=False)
    statut = Column(String, default="CONFIRME")

    patient = relationship("User", foreign_keys=[patient_id], back_populates="rdv_patients")
    medecin = relationship("User", foreign_keys=[medecin_id], back_populates="rdv_medecins")

    __table_args__ = (
        UniqueConstraint('medecin_id', 'date_heure', name='_medecin_creneau_uc'),
    )


class Consultation(Base):
    __tablename__ = "consultations"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    medecin_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    lieu = Column(String, nullable=True)
    date_consultation = Column(DateTime, default=datetime.utcnow)
    
    symptomes = Column(Text, nullable=False)
    diagnostic = Column(Text, nullable=False)
    prescription = Column(Text, nullable=True)

    patient = relationship("User", foreign_keys=[patient_id], back_populates="consultations_recues")
    medecin = relationship("User", foreign_keys=[medecin_id], back_populates="consultations_donnees")