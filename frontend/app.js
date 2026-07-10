document.addEventListener("DOMContentLoaded", () => {
    // 1. CONFIGURATION DE LA CONNEXION (Ton serveur Render)
    const BACKEND_URL = "resonuance.onrender.com"; 
    const USER_ID = "User_" + Math.floor(Math.random() * 1000); // Génère un ID unique temporaire
    
    // Ouverture de la connexion WebSocket en temps réel avec ton backend FastAPI
    const ws = new WebSocket(`wss://${BACKEND_URL}/ws/${USER_ID}`);

    const sendBtn = document.getElementById("send-btn");
    const messageInput = document.getElementById("message-input");
    const chatContainer = document.getElementById("chat-container");

    // 2. ÉCOUTER LES MESSAGES EN PROVENANCE DU SERVEUR
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        // Créer une nouvelle bulle de message
        const messageDiv = document.createElement("div");
        messageDiv.classList.add("message");

        // Si c'est nous qui l'avons envoyé -> à droite (sent), sinon -> à gauche (received)
        if (data.sender_id === USER_ID) {
            messageDiv.classList.add("sent");
            messageDiv.innerHTML = `${data.text} <span class="vibe-tag">${data.vibe}</span>`;
        } else {
            messageDiv.classList.add("received");
            messageDiv.innerHTML = `<strong>${data.sender_id}:</strong> ${data.text} <span class="vibe-tag">${data.vibe}</span>`;
        }

        // Ajouter le message à l'écran et faire défiler vers le bas
        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    };

    ws.onopen = () => {
        console.log("Connecté au serveur de chat Résonuance !");
    };

    ws.onerror = (error) => {
        console.error("Erreur de connexion au chat :", error);
    };

    // 3. ENVOYER UN MESSAGE AU SERVEUR QUAND ON CLIQUE SUR LE BOUTON
    sendBtn.addEventListener("click", () => {
        const text = messageInput.value.trim();
        if (text === "" || ws.readyState !== WebSocket.OPEN) return;

        // Structure du message attendue par le backend Python
        const payload = {
            text: text,
            recipient_id: null // Envoi dans le salon public pour l'instant
        };

        // Envoi des données converties en texte JSON
        ws.send(JSON.stringify(payload));
        
        // Vider le champ de texte
        messageInput.value = "";
    });

    // Permet d'envoyer le message en appuyant sur "Entrée" depuis le clavier de l'iPhone
    messageInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
            sendBtn.click();
        }
    });
});
