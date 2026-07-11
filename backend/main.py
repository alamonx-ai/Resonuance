from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
import json

# --- MONGODB, DATES & IA ---
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import os
from groq import AsyncGroq  # Utilisation du client asynchrone

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
groq_client = AsyncGroq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

if not groq_client:
    print("ATTENTION : GROQ_API_KEY n'est pas détectée par le code !")
else:
    print("Groq initialisé avec succès en mode Asynchrone.")
# ------------------------------


# --- MOTEUR D'ANALYSE PAR INTELLIGENCE ARTIFICIELLE ---
async def analyze_with_ai(text: str) -> dict:
    if not groq_client:
        print("Erreur : groq_client est à None, retour au fallback.")
        return {"emotion": "Cle_Manquante", "need": "Vérifier Render", "interpretation": "GROQ_API_KEY est introuvable"}

    try:
        chat_completion = await groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Tu es l'expert psychologue du chat Résonuance. Tu analyses les messages des utilisateurs. "
                        "Tu devez obligatoirement répondre sous la forme d'un objet JSON pur, sans markdown, sans texte autour. "
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
            model="llama3-8b-8192",
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        ai_response = chat_completion.choices[0].message.content
        print(f"Réponse brute de Groq : {ai_response}")
        return json.loads(ai_response)
        
    except Exception as e:
        error_msg = str(e)[:25].replace(" ", "_") # Évite les espaces problématiques dans la classe CSS
        print(f"Erreur lors de l'appel IA Groq : {e}")
        return {"emotion": f"Err_{error_msg}", "need": "IA en panne", "interpretation": "Exception levée"}
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
            except Exception as e:
                print(f"Erreur d'envoi à {user_id}, déconnexion automatique.")
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
            analysis = await analyze_with_ai(text)

            current_time = datetime.utcnow()

            # Sauvegarde MongoDB
            db_payload = {
                "sender_id": user_id,
                "recipient_id": recipient_id if recipient_id else None,
                "text": text,
                "analysis": analysis,
                "timestamp": current_time
            }

            try:
                await messages_collection.insert_one(db_payload)
            except Exception as e:
                print(f"Erreur MongoDB: {e}")

            # Structure réseau prête
            ws_response = {
                "sender_id": user_id,
                "recipient_id": recipient_id if recipient_id else None,
                "text": text,
                "analysis": analysis,
                "timestamp": current_time.isoformat()
            }

            try:
                message_string = json.dumps(ws_response)
                
                if recipient_id:
                    await manager.send_personal_message(message_string, recipient_id)
                    await manager.send_personal_message(message_string, user_id)
                else:
                    await manager.broadcast(message_string)
                    
            except Exception as e:
                print(f"Erreur lors de la sérialisation ou de l'envoi réseau : {e}")

    except WebSocketDisconnect:
        manager.disconnect(user_id)
