document.addEventListener("DOMContentLoaded", () => {
    const BACKEND_URL = "resonuance.onrender.com"; 
    let ws = null;
    let username = "";

    // Éléments du Login
    const loginContainer = document.getElementById("login-container");
    const usernameInput = document.getElementById("username-input");
    const loginBtn = document.getElementById("login-btn");

    // Éléments du Chat
    const appContainer = document.getElementById("app-container");
    const currentUserTag = document.getElementById("current-user-tag");
    const sendBtn = document.getElementById("send-btn");
    const messageInput = document.getElementById("message-input");
    const chatContainer = document.getElementById("chat-container");

    // Étape 1 : Gérer l'identification de l'utilisateur
    loginBtn.addEventListener("click", () => {
        username = usernameInput.value.trim();
        if (username === "") {
            alert("Choisis un pseudo pour te connecter !");
            return;
        }

        // Masquer le login et afficher le chat
        loginContainer.style.display = "none";
        appContainer.style.display = "flex";
        currentUserTag.textContent = username;

        // Lancer la vraie connexion WebSocket avec le pseudo choisi
        connectToServer(username);
    });

    usernameInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") loginBtn.click();
    });

    // Étape 2 : Connexion au serveur Python
    function connectToServer(userId) {
        ws = new WebSocket(`wss://${BACKEND_URL}/ws/${userId}`);

        ws.onopen = () => {
            console.log("Connexion établie avec succès !");
            appendSystemMessage("Connexion au serveur Résonuance réussie.");
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            const messageDiv = document.createElement("div");
            messageDiv.classList.add("message");

            // On récupère l'émotion depuis le nouvel objet "analysis" envoyé par Python
            const emotion = data.analysis && data.analysis.emotion ? data.analysis.emotion : "Neutre";

            // Si le message vient de nous-mêmes
            if (data.sender_id === username) {
                messageDiv.classList.add("sent");
                messageDiv.innerHTML = `${data.text} <span class="vibe-tag">${emotion}</span>`;
            } else {
                // Si ça vient d'un autre utilisateur connecté
                messageDiv.classList.add("received");
                messageDiv.innerHTML = `<strong>${data.sender_id}:</strong> ${data.text} <span class="vibe-tag">${emotion}</span>`;
            }

            chatContainer.appendChild(messageDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        };

        ws.onerror = (error) => {
            console.error("Erreur de connexion :", error);
            appendSystemMessage("Erreur : Impossible de joindre le serveur.");
        };

        ws.onclose = () => {
            appendSystemMessage("Déconnecté du serveur. Tentative de reconnexion...");
            setTimeout(() => connectToServer(username), 4000);
        };
    }

    // Étape 3 : Envoi des messages
    sendBtn.addEventListener("click", () => {
        const text = messageInput.value.trim();
        if (text === "") return;

        if (ws && ws.readyState === WebSocket.OPEN) {
            const payload = {
                text: text,
                recipient_id: "" // Une chaîne vide évite les conflits d'aiguillage en Python
            };
            ws.send(JSON.stringify(payload));
            messageInput.value = "";
        } else {
            alert("Le chat est hors-ligne pour le moment. Attente du serveur...");
        }
    });

    messageInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") sendBtn.click();
    });

    function appendSystemMessage(text) {
        const msg = document.createElement("div");
        msg.style.textAlign = "center"; // Correction d'une petite erreur de syntaxe CSS ici !
        msg.style.fontSize = "0.8rem";
        msg.style.color = "#999";
        msg.style.margin = "10px 0";
        msg.textContent = text;
        chatContainer.appendChild(msg);
    }
});
