const API_URL = "/api";

function setAuthSession(token, role, nom, prenom) {
    localStorage.setItem("token", token);
    localStorage.setItem("role", role);
    localStorage.setItem("user_name", `${prenom} ${nom}`);
}

function clearAuthSession() { localStorage.clear(); }
function getToken() { return localStorage.getItem("token"); }
function getRole() { return localStorage.getItem("role"); }

function showAlert(message, type = "danger") {
    const alertBox = document.getElementById("alert-box");
    alertBox.textContent = message;
    alertBox.className = `alert alert-${type}`;
    alertBox.classList.remove("hidden");
    setTimeout(() => alertBox.classList.add("hidden"), 5000);
}

function showView(viewName) {
    const views = [
        "view-login", "view-register", "view-forgot-password",
        "view-reset-password", "view-patient-dashboard", "view-medecin-dashboard"
    ];
    views.forEach(v => {
        const el = document.getElementById(v);
        if (el) el.classList.add("hidden");
    });

    const targetView = document.getElementById(`view-${viewName}`);
    if (targetView) targetView.classList.remove("hidden");

    const userNav = document.getElementById("user-nav");
    if (getToken()) {
        userNav.classList.remove("hidden");
        document.getElementById("user-display-name").textContent = localStorage.getItem("user_name") || "";
    } else {
        userNav.classList.add("hidden");
    }
}

function toggleSpecialiteField() {
    const role = document.getElementById("reg-role").value;
    document.getElementById("group-specialite").classList.toggle("hidden", role !== "MEDECIN");
}

async function handleLogin(event) {
    event.preventDefault();
    const email = document.getElementById("login-email").value;
    const password = document.getElementById("login-password").value;

    try {
        const res = await fetch(`${API_URL}/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Erreur de connexion.");

        setAuthSession(data.access_token, data.role, data.nom, data.prenom);
        showAlert("Connexion réussie !", "success");
        initDashboard();
    } catch (err) {
        showAlert(err.message, "danger");
    }
}

async function handleRegister(event) {
    event.preventDefault();
    const payload = {
        nom: document.getElementById("reg-nom").value,
        prenom: document.getElementById("reg-prenom").value,
        email: document.getElementById("reg-email").value,
        password: document.getElementById("reg-password").value,
        role: document.getElementById("reg-role").value,
        specialite: document.getElementById("reg-role").value === "MEDECIN" ? document.getElementById("reg-specialite").value : null
    };

    try {
        const res = await fetch(`${API_URL}/auth/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Erreur d'inscription.");

        showAlert("Compte créé avec succès !", "success");
        showView("login");
    } catch (err) {
        showAlert(err.message, "danger");
    }
}

async function handleForgotPassword(event) {
    event.preventDefault();
    const email = document.getElementById("forgot-email").value;
    try {
        const res = await fetch(`${API_URL}/auth/forgot-password`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email })
        });
        const data = await res.json();
        showAlert(data.message, "success");
    } catch (err) {
        showAlert("Erreur lors de l'envoi.", "danger");
    }
}

async function handleResetPassword(event) {
    event.preventDefault();
    const token = document.getElementById("reset-token").value;
    const new_password = document.getElementById("reset-new-password").value;
    try {
        const res = await fetch(`${API_URL}/auth/reset-password`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ token, new_password })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Échec.");
        showAlert("Mot de passe mis à jour !", "success");
        showView("login");
    } catch (err) {
        showAlert(err.message, "danger");
    }
}

async function handleCreateCreneau(event) {
    event.preventDefault();
    const debut = document.getElementById("creneau-debut").value;
    const fin = document.getElementById("creneau-fin").value;

    try {
        const res = await fetch(`${API_URL}/creneaux`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${getToken()}`
            },
            body: JSON.stringify({ date_heure_debut: debut, date_heure_fin: fin })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Création impossible.");
        showAlert("Créneau ajouté avec succès !", "success");
    } catch (err) {
        showAlert(err.message, "danger");
    }
}

async function loadDoctorsList() {
    try {
        const res = await fetch(`${API_URL}/medecins`);
        const doctors = await res.json();
        const select = document.getElementById("rdv-medecin-select");
        select.innerHTML = `<option value="">-- Sélectionnez un médecin --</option>`;
        doctors.forEach(doc => {
            select.innerHTML += `<option value="${doc.id}">Dr. ${doc.prenom} ${doc.nom} (${doc.specialite || 'Généraliste'})</option>`;
        });
    } catch (err) {
        showAlert("Erreur lors du chargement des médecins.", "danger");
    }
}

async function loadDoctorCreneaux(medecinId) {
    const select = document.getElementById("rdv-creneau-select");
    if (!medecinId) {
        select.innerHTML = `<option value="">-- Sélectionnez d'abord un médecin --</option>`;
        return;
    }

    try {
        const res = await fetch(`${API_URL}/medecins/${medecinId}/creneaux`);
        const creneaux = await res.json();
        select.innerHTML = `<option value="">-- Sélectionnez un créneau disponible --</option>`;
        creneaux.forEach(c => {
            const d = new Date(c.date_heure_debut).toLocaleString();
            select.innerHTML += `<option value="${c.id}">${d}</option>`;
        });
    } catch (err) {
        showAlert("Erreur lors du chargement des créneaux.", "danger");
    }
}

function logout() {
    clearAuthSession();
    showAlert("Déconnexion effectuée.", "success");
    showView("login");
}

function initDashboard() {
    const role = getRole();
    if (role === "PATIENT") {
        showView("patient-dashboard");
        loadDoctorsList();
    } else if (role === "MEDECIN") {
        showView("medecin-dashboard");
    } else {
        showView("login");
    }
}

window.addEventListener("DOMContentLoaded", () => {
    const urlParams = new URLSearchParams(window.location.search);
    const resetToken = urlParams.get("token");
    if (resetToken) {
        document.getElementById("reset-token").value = resetToken;
        showView("reset-password");
    } else if (getToken()) {
        initDashboard();
    } else {
        showView("login");
    }
});