from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, nullable=False)
    prenom = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False)  # PATIENT ou MEDECIN
    specialite = Column(String, nullable=True)  # Pour les médecins
    hopital = Column(String, nullable=True)     # Hôpital/Établissement d'exercice du médecin

    creneaux = relationship("Creneau", back_populates="medecin", cascade="all, delete-orphan")
    dossier_medical = relationship("DossierMedical", back_populates="patient", uselist=False)

class Creneau(Base):
    __tablename__ = "creneaux"

    id = Column(Integer, primary_key=True, index=True)
    medecin_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date_heure_debut = Column(DateTime, nullable=False)
    date_heure_fin = Column(DateTime, nullable=False)
    est_disponible = Column(Boolean, default=True)

    medecin = relationship("User", back_populates="creneaux")

class RendezVous(Base):
    __tablename__ = "rendez_vous"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    medecin_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    creneau_id = Column(Integer, ForeignKey("creneaux.id"), nullable=True)
    hopital = Column(String, nullable=True)  # Lieu exact de la consultation
    motif = Column(String, nullable=False)
    statut = Column(String, default="EN_ATTENTE")  # EN_ATTENTE, CONFIRME, TERMINE, ANNULE
    symptomes = Column(String, nullable=True)
    diagnostic = Column(String, nullable=True)
    prescription = Column(String, nullable=True)

class DossierMedical(Base):
    """
    Dossier médical définitif et permanent du patient.
    """
    __tablename__ = "dossiers_medicaux"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    groupe_sanguin = Column(String, nullable=True)
    antecedents = Column(Text, nullable=True)      # Antécédents médicaux / chirurgicaux
    allergies = Column(Text, nullable=True)        # Allergies connues
    notes_medecin = Column(Text, nullable=True)    # Historique global des consultations

    patient = relationship("User", back_populates="dossier_medical")