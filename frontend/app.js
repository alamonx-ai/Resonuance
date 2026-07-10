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

        loginContainer.style.display = "none";
        appContainer.style.display = "flex";
        currentUserTag.textContent = username;

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
            console.log("Données brutes reçues du WS :", event.data);
            const data = JSON.parse(event.data);
            const emotion = data.analysis && data.analysis.emotion ? data.analysis.emotion : "Neutre";
            
            if (data.sender_id === username) {
                // On cherche l'élément le plus récent en attente
                const pendingMessages = document.querySelectorAll(".message.sent.pending-analysis");
                if (pendingMessages.length > 0) {
                    const localMsg = pendingMessages[pendingMessages.length - 1];
                    const vibeTag = localMsg.querySelector(".vibe-tag");
                    if (vibeTag) {
                        vibeTag.textContent = emotion;
                        vibeTag.className = `vibe-tag ${emotion.toLowerCase()}`;
                    }
                    localMsg.classList.remove("pending-analysis");
                }
            } else {
                const messageDiv = document.createElement("div");
                messageDiv.classList.add("message", "received");
                messageDiv.innerHTML = `<strong>${data.sender_id}:</strong> ${data.text} <span class="vibe-tag ${emotion.toLowerCase()}">${emotion}</span>`;
                
                chatContainer.appendChild(messageDiv);
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
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

        // Création de la bulle locale
        const messageDiv = document.createElement("div");
        messageDiv.classList.add("message", "sent", "pending-analysis");
        messageDiv.innerHTML = `${text} <span class="vibe-tag">Analyse...</span>`;
        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;

        if (ws && ws.readyState === WebSocket.OPEN) {
            const payload = {
                text: text,
                recipient_id: "" 
            };
            console.log("Envoi du payload au serveur :", payload);
            ws.send(JSON.stringify(payload));
        } else {
            console.log("Serveur déconnecté, affichage local uniquement.");
            const vibeTag = messageDiv.querySelector(".vibe-tag");
            if (vibeTag) vibeTag.textContent = "Hors-ligne";
        }
        
        messageInput.value = "";
    });

    messageInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") sendBtn.click();
    });

    function appendSystemMessage(text) {
        const msg = document.createElement("div");
        msg.style.textAlign = "center";
        msg.style.fontSize = "0.8rem";
        msg.style.color = "#999";
        msg.style.margin = "10px 0";
        msg.textContent = text;
        chatContainer.appendChild(msg);
    }
});
