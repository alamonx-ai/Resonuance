from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
import json

# --- MONGODB, DATES & IA ---
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import os
from groq import Groq

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

# --- INITIALISATION IA GROQ ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
# Si la clé est manquante en local, on ne bloque pas le démarrage mais on prévient
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
# ------------------------------


# --- MOTEUR D'ANALYSE PAR INTELLIGENCE ARTIFICIELLE ---
def analyze_with_ai(text: str) -> dict:
    # Structure de secours si l'IA ne répond pas
    fallback = {"emotion": "Neutre", "need": "Non identifié", "interpretation": "Analyse indisponible"}
    
    if not groq_client:
        return fallback

    try:
        # On demande à Llama 3 d'analyser psychologiquement le message
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Tu es l'expert psychologue du chat Résonuance. Tu analyses les messages des utilisateurs. "
                        "Tu dois obligatoirement répondre sous la forme d'un objet JSON pur, sans markdown, sans texte autour. "
                        "Le JSON doit suivre exactement cette structure : "
                        '{"emotion": "Un seul mot (ex: Joie, Colère, Tristesse, Stress, Excitation, Peur, Neutre)", '
                        '"need": "Le besoin psychologique sous-jacent en une courte phrase (ex: Besoin de reconnaissance, besoin d\'écoute)", '
                        '"interpretation": "Une très courte phrase analysant l\'état de l\'utilisateur"}'
                    )
                },
                {
                    "role": "user",
                    "content": f"Analyse ce message : '{text}'"
                }
            ],
            model="llama3-8b-8192", # Modèle ultra rapide et gratuit
            temperature=0.2, # Basse température pour forcer la stabilité du JSON
            response_format={"type": "json_object"} # Force le format JSON
        )
        
        # Récupération et conversion de la réponse de l'IA
        ai_response = chat_completion.choices[0].message.content
        return json.loads(ai_response)
        
    except Exception as e:
        print(f"Erreur IA Groq : {e}")
        return fallback
# ------------------------------------------------------


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
        for user_id, connection in list(self.active_connections.items()):
            try:
                await connection.send_text(message)
            except Exception:
                self.disconnect(user_id)


manager = ConnectionManager()

@app.get("/")
def read_root():
    return {"status": "Resonuance AI Backend en ligne !"}

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(user_id, websocket)

    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
            except Exception:
                continue

            text = message_data.get("text", "").strip()
            recipient_id = message_data.get("recipient_id", "").strip()

            if not text:
                continue

            # --- APPEL DE LA VRAIE IA ---
            analysis = analyze_with_ai(text)
            # ----------------------------

            current_time = datetime.utcnow()

            db_payload = {
                "sender_id": user_id,
                "recipient_id": recipient_id if recipient_id else None,
                "text": text,
                "analysis": analysis, # Contient emotion, need, et interpretation générés par l'IA
                "timestamp": current_time
            }

            try:
                await messages_collection.insert_one(db_payload)
            except Exception as e:
                print(f"Erreur MongoDB: {e}")

            ws_response = {
                "sender_id": user_id,
                "recipient_id": recipient_id if recipient_id else None,
                "text": text,
                "analysis": analysis,
                "timestamp": current_time.isoformat()
            }

            message_string = json.dumps(ws_response)

            if recipient_id:
                await manager.send_personal_message(message_string, recipient_id)
                await manager.send_personal_message(message_string, user_id)
            else:
                await manager.broadcast(message_string)

    except WebSocketDisconnect:
        manager.disconnect(user_id)
