from typing import List

# (garder tous les imports et routes d'authentification existants)

@app.get("/api/medecin/rdv", response_model=List[schemas.RdvOut])
def get_medecin_rdv(db: Session = Depends(get_db)):
    rdvs = db.query(models.RendezVous).all()
    result = []
    for r in rdvs:
        patient = db.query(models.User).filter(models.User.id == r.patient_id).first()
        result.append({
            "id": r.id,
            "date_heure": r.date_heure,
            "motif": r.motif,
            "statut": r.statut.value if hasattr(r.statut, 'value') else str(r.statut),
            "patient_id": r.patient_id,
            "nom_patient": patient.nom if patient else "Inconnu",
            "prenom_patient": patient.prenom if patient else ""
        })
    return result

@app.post("/api/medecin/consultation", response_model=schemas.ConsultationOut)
def create_consultation(data: schemas.ConsultationCreate, db: Session = Depends(get_db)):
    rdv = db.query(models.RendezVous).filter(models.RendezVous.id == data.rdv_id).first()
    if not rdv:
        raise HTTPException(status_code=404, detail="Rendez-vous introuvable")

    consultation = models.Consultation(
        rdv_id=data.rdv_id,
        symptomes=data.symptomes,
        diagnostic=data.diagnostic,
        prescription=data.prescription
    )
    rdv.statut = models.StatusRdv.TERMINE
    
    db.add(consultation)
    db.commit()
    db.refresh(consultation)
    return consultation

# Route temporaire pour créer des rendez-vous de démonstration
@app.post("/api/dev/seed-rdv")
def seed_rdv(db: Session = Depends(get_db)):
    patient = db.query(models.User).filter(models.User.role == models.RoleEnum.PATIENT).first()
    medecin = db.query(models.User).filter(models.User.role == models.RoleEnum.MEDECIN).first()
    
    if not patient or not medecin:
        return {"message": "Créez au moins un Patient et un Médecin avant d'exécuter ce test."}

    rdv1 = models.RendezVous(motif="Consultation générale", patient_id=patient.id, medecin_id=medecin.id)
    rdv2 = models.RendezVous(motif="Suivi de contrôle", patient_id=patient.id, medecin_id=medecin.id)
    
    db.add_all([rdv1, rdv2])
    db.commit()
    return {"message": "Rendez-vous de test créés avec succès !"}