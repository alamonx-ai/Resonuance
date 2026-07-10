document.addEventListener("DOMContentLoaded", () => {
    const BACKEND_URL = "resonuance.onrender.com"; 
    const USER_ID = "User_" + Math.floor(Math.random() * 1000); 
    
    let ws;
    const sendBtn = document.getElementById("send-btn");
    const messageInput = document.getElementById("message-input");
    const chatContainer = document.getElementById("chat-container");

    // Fonction pour afficher un message à l'écran
    function appendMessage(senderId, text, vibe) {
        const messageDiv = document.createElement("div");
        messageDiv.classList.add("message");

        if (senderId === USER_ID) {
            messageDiv.classList.add("sent");
            messageDiv.innerHTML = `${text} <span class="vibe-tag">${vibe}</span>`;
        } else {
            messageDiv.classList.add("received");
            messageDiv.innerHTML = `<strong>${senderId}:</strong> ${text} <span class="vibe-tag">${vibe}</span>`;
        }

        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    // Fonction pour initialiser la connexion WebSocket
    function connectWebSocket() {
        ws = new WebSocket(`wss://${BACKEND_URL}/ws/${USER_ID}`);

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            // Si on reçoit le message du serveur, et que c'est le nôtre, on évite de le doubler
            // si on l'a déjà affiché en local. Pour l'instant, on laisse le serveur gérer.
            appendMessage(data.sender_id, data.text, data.vibe);
        };

        ws.onopen = () => {
            console.log("Connecté au serveur de chat Résonuance !");
        };

        ws.onerror = (error) => {
            console.error("Erreur WebSocket :", error);
        };

        ws.onclose = () => {
            console.log("Connexion fermée. Tentative de reconnexion dans 5 secondes...");
            setTimeout(connectWebSocket, 5000); // Reconnexion automatique
        };
    }

    // Lancer la connexion
    connectWebSocket();

    // Gestion de l'envoi
    sendBtn.addEventListener("click", () => {
        const text = messageInput.value.trim();
        if (text === "") return;

        // Si le WebSocket est ouvert, on envoie au serveur Python
        if (ws && ws.readyState === WebSocket.OPEN) {
            const payload = {
                text: text,
                recipient_id: null
            };
            ws.send(JSON.stringify(payload));
        } else {
            // MODE SECOURS : Si Render dort ou bug, on affiche quand même le message
            // pour que tu puisses voir que ton bouton et ton design fonctionnent !
            console.warn("Serveur déconnecté. Affichage en mode local.");
            appendMessage(USER_ID, text, "Local (Hors-ligne)");
        }
        
        messageInput.value = "";
    });

    messageInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
            sendBtn.click();
        }
    });
});
