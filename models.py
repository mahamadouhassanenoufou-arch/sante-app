from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(100), nullable=False)
    prenom = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    telephone = Column(String(20), nullable=True)
    hashed_password = Column(String(255), nullable=True)
    role = Column(String(20), default="patient", nullable=True)

    rendez_vous = relationship("RendezVous", back_populates="patient")

class Medecin(Base):
    __tablename__ = "medecins"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(100), nullable=False)
    prenom = Column(String(100), nullable=False)
    specialite = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)

    rendez_vous = relationship("RendezVous", back_populates="medecin")
    disponibilites = relationship("Disponibilite", back_populates="medecin", cascade="all, delete-orphan")

class RendezVous(Base):
    __tablename__ = "rendez_vous"

    id = Column(Integer, primary_key=True, index=True)
    date_heure = Column(DateTime, nullable=False)
    motif = Column(String(255), nullable=False)
    statut = Column(String(50), default="Programmé")
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    medecin_id = Column(Integer, ForeignKey("medecins.id"), nullable=False)

    patient = relationship("Patient", back_populates="rendez_vous")
    medecin = relationship("Medecin", back_populates="rendez_vous")
    notes = relationship("ConsultationNote", back_populates="rendez_vous", cascade="all, delete-orphan")

class Disponibilite(Base):
    __tablename__ = "disponibilites"

    id = Column(Integer, primary_key=True, index=True)
    medecin_id = Column(Integer, ForeignKey("medecins.id"), nullable=False)
    jour_semaine = Column(String(20), nullable=False)  # ex: "Lundi", "Mardi"
    heure_debut = Column(String(5), nullable=False)   # ex: "08:00"
    heure_fin = Column(String(5), nullable=False)     # ex: "17:00"

    medecin = relationship("Medecin", back_populates="disponibilites")

class ConsultationNote(Base):
    __tablename__ = "consultation_notes"

    id = Column(Integer, primary_key=True, index=True)
    rendez_vous_id = Column(Integer, ForeignKey("rendez_vous.id"), nullable=False)
    diagnostic = Column(Text, nullable=False)
    prescription = Column(Text, nullable=True)
    date_creation = Column(DateTime, nullable=False)

    rendez_vous = relationship("RendezVous", back_populates="notes")