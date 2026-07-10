from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
import json

app = FastAPI()

# Permettre au frontend (Vercel) de se connecter au backend (Render)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # On pourra restreindre à ton URL Vercel plus tard
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Structure pour stocker les connexions actives des utilisateurs
class ConnectionManager:
    def __init__(self):
        # Associe un ID utilisateur à sa connexion WebSocket active
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_personal_message(self, message: str, user_id: str):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_text(message)

    async def broadcast(self, message: str):
        # Envoie un message à tout le monde connecté
        for connection in self.active_connections.values():
            await connection.send_text(message)

manager = ConnectionManager()

@app.get("/")
def read_root():
    return {"status": "Résonuance Backend en ligne !"}

# Route WebSocket pour le chat en temps réel
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(user_id, websocket)
    try:
        while True:
            # Attendre de recevoir un message du client (HTML/JS)
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Format attendu du message : {"text": "Bonjour", "recipient_id": "user2"}
            text = message_data.get("text")
            recipient_id = message_data.get("recipient_id")

            # TODO: Ici on viendra injecter l'analyse de personnalité (Big Five)
            # Pour l'instant, on prépare la réponse
            response = {
                "sender_id": user_id,
                "text": text,
                "vibe": "Neutre" # Ce paramètre changera selon la nuance détectée
            }

            # Envoyer le message au destinataire
            if recipient_id:
                await manager.send_personal_message(json.dumps(response), recipient_id)
                # On renvoie aussi le message à l'expéditeur pour confirmation
                await manager.send_personal_message(json.dumps(response), user_id)
            else:
                # Si pas de destinataire précis, on l'envoie à tout le monde (mode salon public)
                await manager.broadcast(json.dumps(response))

    except WebSocketDisconnect:
        manager.disconnect(user_id)
