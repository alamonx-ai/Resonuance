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
        # Utilisation de list() pour éviter les erreurs de modification de dictionnaire en cours de boucle
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
            
            # Sécurité décodage JSON
            try:
                message_data = json.loads(data)
            except Exception:
                continue

            text = message_data.get("text", "").strip()
            recipient_id = message_data.get("recipient_id", "").strip()

            # On ignore les messages vides
            if not text:
                continue

            current_time = datetime.utcnow()

            # 1. Payload pour MongoDB (contient l'objet datetime brut)
            db_payload = {
                "sender_id": user_id,
                "recipient_id": recipient_id if recipient_id else None,
                "text": text,
                "analysis": {
                    "emotion": "Neutre",
                    "need": None,
                    "interpretation": None
                },
                "timestamp": current_time
            }

            # Sauvegarde MongoDB isolée pour ne pas polluer l'envoi WebSocket avec l' _id
            try:
                await messages_collection.insert_one(db_payload)
            except Exception as e:
                print(f"Erreur MongoDB: {e}")

            # 2. Payload propre pour le WebSocket (sans l'objet _id de MongoDB)
            ws_response = {
                "sender_id": user_id,
                "recipient_id": recipient_id if recipient_id else None,
                "text": text,
                "analysis": {
                    "emotion": "Neutre",
                    "need": None,
                    "interpretation": None
                },
                "timestamp": current_time.isoformat()
            }

            message_string = json.dumps(ws_response)

            # Aiguillage du message
            if recipient_id:
                # Salon privé
                await manager.send_personal_message(message_string, recipient_id)
                await manager.send_personal_message(message_string, user_id)
            else:
                # Salon public
                await manager.broadcast(message_string)

    except WebSocketDisconnect:
        manager.disconnect(user_id)
