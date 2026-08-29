// --- 1. Enregistrement du Service Worker ---
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
            .then(reg => console.log('Service Worker enregistré sur :', reg.scope))
            .catch(err => console.error('Erreur Service Worker :', err));
    });
}

// --- 2. Gestion de l'état du réseau (Online / Offline) ---
const statusIndicator = document.getElementById('status-indicator');

function updateOnlineStatus() {
    if (navigator.onLine) {
        statusIndicator.textContent = "Connecté au réseau";
        statusIndicator.className = "status-bar online";
        syncPendingData(); // Tente de synchroniser dès que le réseau revient
    } else {
        statusIndicator.textContent = "Hors-ligne (Sauvegarde locale activée)";
        statusIndicator.className = "status-bar offline";
    }
}

window.addEventListener('online', updateOnlineStatus);
window.addEventListener('offline', updateOnlineStatus);
updateOnlineStatus(); // Vérification initiale au chargement

// --- 3. Soumission du formulaire et stockage hors-ligne ---
const dataForm = document.getElementById('data-form');

dataForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const payload = {
        title: document.getElementById('title').value,
        details: document.getElementById('details').value,
        timestamp: new Date().toISOString()
    };

    if (navigator.onLine) {
        // Envoi direct au serveur FastAPI
        await sendDataToServer(payload);
    } else {
        // Sauvegarde dans le localStorage si hors-ligne
        saveOfflineData(payload);
        alert('Réseau indisponible : les données ont été enregistrées localement et seront envoyées dès le retour du réseau.');
    }

    dataForm.reset();
});

// --- 4. Fonctions d'envoi et de synchronisation ---
async function sendDataToServer(data) {
    try {
        const response = await fetch('/api/data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            throw new Error(`Erreur serveur: ${response.status}`);
        }

        console.log('Données transmises avec succès au backend !');
        return true;
    } catch (error) {
        console.error('Échec de l\'envoi réseau, sauvegarde en local :', error);
        saveOfflineData(data);
        return false;
    }
}

function saveOfflineData(data) {
    const pendingData = JSON.parse(localStorage.getItem('pending_requests') || '[]');
    pendingData.push(data);
    localStorage.setItem('pending_requests', JSON.stringify(pendingData));
}

async function syncPendingData() {
    const pendingData = JSON.parse(localStorage.getItem('pending_requests') || '[]');
    if (pendingData.length === 0) return;

    console.log(`Tentative de synchronisation de ${pendingData.length} élément(s)...`);
    const remainingData = [];

    for (const item of pendingData) {
        const success = await sendDataToServer(item);
        if (!success) {
            remainingData.push(item);
        }
    }

    localStorage.setItem('pending_requests', JSON.stringify(remainingData));

    if (remainingData.length === 0) {
        console.log('Toutes les données hors-ligne ont été synchronisées avec succès.');
    }
}