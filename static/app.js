// --- 1. Enregistrement du Service Worker ---
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
            .then(reg => console.log('Service Worker PWA actif :', reg.scope))
            .catch(err => console.error('Erreur Service Worker :', err));
    });
}

// --- 2. Chargement des données dynamiques depuis FastAPI ---
document.addEventListener('DOMContentLoaded', () => {
    loadPatientData();
});

async function loadPatientData() {
    try {
        const response = await fetch('/api/patient/dashboard');
        if (response.ok) {
            const data = await response.json();
            console.log('Données Patient chargées :', data);
            // Possibilité d'injecter data.prochain_rdv directement dans le DOM
        }
    } catch (error) {
        console.warn('Mode hors-ligne : données locales affichées.');
    }
}

async function loadMedecinData() {
    try {
        const response = await fetch('/api/medecin/dashboard');
        if (response.ok) {
            const data = await response.json();
            console.log('Données Médecin chargées :', data);
        }
    } catch (error) {
        console.warn('Mode hors-ligne : données locales affichées.');
    }
}

// --- 3. Gestion du changement d'onglet ---
function switchRole(role) {
    const viewPatient = document.getElementById('view-patient');
    const viewMedecin = document.getElementById('view-medecin');
    const tabPatient = document.getElementById('tab-patient');
    const tabMedecin = document.getElementById('tab-medecin');

    if (role === 'patient') {
        viewPatient.classList.remove('hidden');
        viewMedecin.classList.add('hidden');
        tabPatient.classList.add('active');
        tabMedecin.classList.remove('active');
        loadPatientData();
    } else {
        viewPatient.classList.add('hidden');
        viewMedecin.classList.remove('hidden');
        tabMedecin.classList.add('active');
        tabPatient.classList.remove('active');
        loadMedecinData();
    }
}

// --- 4. Modales de création rapides ---
async function handleNewRdv() {
    const medecin = prompt("Nom du médecin ou spécialité :");
    if (!medecin) return;

    const payload = {
        type: "rendez_vous",
        medecin: medecin,
        date: new Date().toISOString()
    };

    await sendPayload(payload);
}

async function handleNewConsultation() {
    const patientName = prompt("Nom du patient :");
    const notes = prompt("Notes de consultation / Diagnostic :");
    if (!patientName) return;

    const payload = {
        type: "consultation",
        patient: patientName,
        notes: notes,
        date: new Date().toISOString()
    };

    await sendPayload(payload);
}

async function sendPayload(payload) {
    try {
        const response = await fetch('/api/data', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            alert("Enregistrement réussi !");
        } else {
            throw new Error("Erreur serveur");
        }
    } catch (error) {
        // Sauvegarde hors-ligne temporaire
        const pending = JSON.parse(localStorage.getItem('pending_requests') || '[]');
        pending.push(payload);
        localStorage.setItem('pending_requests', JSON.stringify(pending));
        alert("Hors-ligne : enregistrement sauvegardé localement.");
    }
}