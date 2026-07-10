from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
import json

# --- MONGODB & DATES ---
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import os

app = FastAPI()

# Permettre au frontend (Vercel) de se connecter au backend (Render)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre plus tard à ton domaine Vercel
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- INITIALISATION MONGODB ---
MONGO_DETAILS = os.environ.get("MONGO_URI")

if not MONGO_DETAILS:
    raise Exception("MONGO_URI manquant")

client = AsyncIOMotorClient(MONGO_DETAILS)
db = client.resonuance

messages_collection = db.get_collection("messages")
users_collection = db.get_collection("users")
# ------------------------------


# Structure pour stocker les connexions actives
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_personal_message(self, message: str, user_id: str):
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_text(message)
            except Exception:
                self.disconnect(user_id)

    async def broadcast(self, message: str):
        # On utilise une liste des connexions pour éviter les bugs pendant la boucle
        for user_id, connection in list(self.active_connections.items()):
            try:
                await connection.send_text(message)
            except Exception:
                self.disconnect(user_id)


manager = ConnectionManager()


@app.get("/")
def read_root():
    return {
        "status": "Resonuance Backend en ligne et connecté à MongoDB !"
    }


# Chat temps réel
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(user_id, websocket)

    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)

            text = message_data.get("text")
            recipient_id = message_data.get("recipient_id")

            # On génère le timestamp actuel
            current_time = datetime.utcnow()

            # Structure propre pour MongoDB (avec un vrai objet datetime)
            db_payload = {
                "sender_id": user_id,
                "recipient_id": recipient_id,
                "text": text,
                "analysis": {
                    "emotion": "Neutre",
                    "need": None,
                    "interpretation": None
                },
                "timestamp": current_time
            }

            # Sauvegarde MongoDB (on le laisse injecter son _id ici, on s'en fiche)
            await messages_collection.insert_one(db_payload)

            # Structure propre au format TEXTE pour le WebSocket (évite le bug de l'ObjectId)
            ws_response = {
                "sender_id": user_id,
                "recipient_id": recipient_id,
                "text": text,
                "vibe": "Neutre",  # On garde la clé "vibe" attendue par ton app.js pour l'instant
                "analysis": {
                    "emotion": "Neutre",
                    "need": None,
                    "interpretation": None
                },
                "timestamp": current_time.isoformat()
            }

            # Envoi au destinataire ou en public
            message_string = json.dumps(ws_response)

            if recipient_id:
                # Privé : Destinataire + Expéditeur
                await manager.send_personal_message(message_string, recipient_id)
                await manager.send_personal_message(message_string, user_id)
            else:
                # Public : Tout le monde
                await manager.broadcast(message_string)

    except WebSocketDisconnect:
        manager.disconnect(user_id)
