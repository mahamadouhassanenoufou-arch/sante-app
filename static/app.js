const API_URL = "http://127.0.0.1:8000";
let token = localStorage.getItem("token") || "";
let currentUserRole = "";

document.addEventListener("DOMContentLoaded", () => {
    if (token) loadDashboard();
});

async function login() {
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;
    const errorEl = document.getElementById("auth-error");

    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);

    try {
        const res = await fetch(`${API_URL}/token`, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: formData
        });

        if (!res.ok) throw new Error("Identifiants incorrects");
        const data = await res.json();
        
        token = data.access_token;
        localStorage.setItem("token", token);
        errorEl.classList.add("hidden");
        loadDashboard();
    } catch (err) {
        errorEl.textContent = err.message;
        errorEl.classList.remove("hidden");
    }
}

function logout() {
    localStorage.removeItem("token");
    token = "";
    currentUserRole = "";
    document.getElementById("auth-section").classList.remove("hidden");
    document.getElementById("dashboard-section").classList.add("hidden");
}

async function loadDashboard() {
    document.getElementById("auth-section").classList.add("hidden");
    document.getElementById("dashboard-section").classList.remove("hidden");

    // 1. Récupérer le profil utilisateur et son rôle
    const userRes = await fetchWithAuth("/me");
    if (userRes) {
        document.getElementById("user-name").textContent = `${userRes.prenom} ${userRes.nom}`;
        currentUserRole = userRes.role.toLowerCase();
        document.getElementById("user-role").textContent = currentUserRole.toUpperCase();

        // Affichage dynamique des sections selon le rôle
        renderViewsForRole(currentUserRole);
    }

    loadMedecinsWithDispos();
    loadMyRDVWithNotes();
}

function renderViewsForRole(role) {
    const adminView = document.getElementById("admin-view");
    const medecinView = document.getElementById("medecin-view");
    const rdvFormCard = document.getElementById("rdv-form-card");

    adminView.classList.add("hidden");
    medecinView.classList.add("hidden");
    rdvFormCard.classList.remove("hidden");

    if (role === "admin") {
        adminView.classList.remove("hidden");
        medecinView.classList.remove("hidden");
    } else if (role === "medecin") {
        medecinView.classList.remove("hidden");
        rdvFormCard.classList.add("hidden"); // Cache la réservation classique pour les médecins
    }
}

// --- ACTIONS ADMIN ---
async function adminAddDoctor() {
    const nom = document.getElementById("admin-doc-nom").value;
    const prenom = document.getElementById("admin-doc-prenom").value;
    const specialite = document.getElementById("admin-doc-specialite").value;
    const email = document.getElementById("admin-doc-email").value;

    const res = await fetchWithAuth("/medecins/", "POST", { nom, prenom, specialite, email });
    if (res) {
        alert("Médecin créé avec succès !");
        loadMedecinsWithDispos();
    }
}

async function adminAddDispo() {
    const medecin_id = parseInt(document.getElementById("admin-dispo-doc-id").value);
    const jour_semaine = document.getElementById("admin-dispo-jour").value;
    const heure_debut = document.getElementById("admin-dispo-debut").value;
    const heure_fin = document.getElementById("admin-dispo-fin").value;

    const res = await fetchWithAuth(`/medecins/${medecin_id}/disponibilites`, "POST", { jour_semaine, heure_debut, heure_fin });
    if (res) {
        alert("Disponibilité ajoutée avec succès !");
        loadMedecinsWithDispos();
    }
}

// --- ACTIONS MÉDECIN ---
async function docSaveNote() {
    const rendez_vous_id = parseInt(document.getElementById("doc-note-rdv-id").value);
    const diagnostic = document.getElementById("doc-note-diag").value;
    const prescription = document.getElementById("doc-note-presc").value;

    const res = await fetchWithAuth("/consultations/notes", "POST", { rendez_vous_id, diagnostic, prescription });
    if (res) {
        alert("Note enregistrée et rendez-vous terminé avec succès !");
        loadMyRDVWithNotes();
    }
}

// --- CHARGEMENT DES DONNÉES ---
async function loadMedecinsWithDispos() {
    const medecins = await fetchWithAuth("/medecins/");
    const listEl = document.getElementById("medecins-list");

    if (!medecins || medecins.length === 0) {
        listEl.innerHTML = '<li class="py-2 text-slate-500">Aucun médecin disponible.</li>';
        return;
    }

    let html = "";
    for (const m of medecins) {
        const dispos = await fetchWithAuth(`/medecins/${m.id}/disponibilites`) || [];
        
        let disposHtml = dispos.length > 0
            ? dispos.map(d => `<span class="inline-block bg-blue-50 text-blue-600 px-2 py-0.5 rounded text-xs mr-1 mt-1">${d.jour_semaine}: ${d.heure_debut}-${d.heure_fin}</span>`).join('')
            : '<span class="text-xs text-slate-400">Aucun créneau renseigné</span>';

        html += `
            <li class="py-3">
                <div class="flex justify-between items-center mb-1">
                    <span><strong>Dr. ${m.prenom} ${m.nom}</strong> (${m.specialite})</span>
                    <span class="text-xs bg-slate-100 text-slate-600 px-2 py-1 rounded font-mono">ID: ${m.id}</span>
                </div>
                <div>${disposHtml}</div>
            </li>
        `;
    }
    listEl.innerHTML = html;
}

async function loadMyRDVWithNotes() {
    const rdvs = await fetchWithAuth("/rendez-vous/mes-rdv");
    const listEl = document.getElementById("rdv-list");

    if (!rdvs || rdvs.length === 0) {
        listEl.innerHTML = '<li class="py-2 text-slate-500">Aucun rendez-vous.</li>';
        return;
    }

    let html = "";
    for (const r of rdvs) {
        const notes = await fetchWithAuth(`/rendez-vous/${r.id}/notes`) || [];

        let notesHtml = notes.length > 0
            ? notes.map(n => `
                <div class="bg-slate-50 border-l-2 border-blue-500 p-2 mt-2 rounded text-xs space-y-1">
                    <p class="font-semibold text-slate-700">Diagnostic : <span class="font-normal">${n.diagnostic}</span></p>
                    ${n.prescription ? `<p class="font-semibold text-slate-700">Prescription : <span class="font-normal">${n.prescription}</span></p>` : ''}
                </div>
            `).join('')
            : '';

        html += `
            <li class="py-3">
                <div class="flex justify-between items-center">
                    <div>
                        <p class="font-medium text-slate-800">RDV #${r.id} - ${new Date(r.date_heure).toLocaleString()}</p>
                        <p class="text-xs text-slate-500">${r.motif}</p>
                    </div>
                    <span class="text-xs px-2 py-1 rounded ${r.statut === 'Annulé' ? 'bg-red-100 text-red-600' : (r.statut === 'Terminé' ? 'bg-blue-100 text-blue-600' : 'bg-green-100 text-green-600')}">
                        ${r.statut}
                    </span>
                </div>
                ${notesHtml}
            </li>
        `;
    }
    listEl.innerHTML = html;
}

async function createRendezVous() {
    const medecin_id = parseInt(document.getElementById("rdv-medecin-id").value);
    const date_heure = document.getElementById("rdv-date").value;
    const motif = document.getElementById("rdv-motif").value;

    if (!medecin_id || !date_heure || !motif) {
        alert("Veuillez remplir tous les champs.");
        return;
    }

    const res = await fetchWithAuth("/rendez-vous/", "POST", { medecin_id, date_heure, motif });
    if (res) {
        alert("Rendez-vous réservé avec succès !");
        loadMyRDVWithNotes();
    }
}

async function fetchWithAuth(endpoint, method = "GET", body = null) {
    const options = {
        method,
        headers: {
            "Authorization": `Bearer ${token}`,
            "Content-Type": "application/json"
        }
    };
    if (body) options.body = JSON.stringify(body);

    const res = await fetch(`${API_URL}${endpoint}`, options);
    if (res.status === 401) { logout(); return null; }
    if (!res.ok) {
        const err = await res.json();
        alert(err.detail || "Une erreur est survenue");
        return null;
    }
    return await res.json();
}