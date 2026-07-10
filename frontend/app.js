document.addEventListener("DOMContentLoaded", () => {
    const sendBtn = document.getElementById("send-btn");
    const messageInput = document.getElementById("message-input");
    const chatContainer = document.getElementById("chat-container");

    sendBtn.addEventListener("click", () => {
        const text = messageInput.value.trim();
        if (text === "") return;

        // 1. Créer la bulle du message
        const messageDiv = document.createElement("div");
        messageDiv.classList.add("message", "sent");
        messageDiv.innerHTML = `${text} <span class="vibe-tag">Envoi...</span>`;

        // 2. L'ajouter au chat
        chatContainer.appendChild(messageDiv);
        
        // 3. Clear l'input et scroll en bas
        messageInput.value = "";
        chatContainer.scrollTop = chatContainer.scrollHeight;
    });
});
