import random
import string
import uuid
from typing import Dict, Any
from fastapi import APIRouter, File, UploadFile, Form, HTTPException

router = APIRouter()

# In-memory store for MVP
# Structure: { "A7B29": { "status": "active", "sessions": [] } }
active_rooms: Dict[str, Any] = {}

def generate_room_code() -> str:
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        if code not in active_rooms:
            return code

@router.post("/rooms/create")
async def create_room():
    code = generate_room_code()
    active_rooms[code] = {
        "status": "created",
        "sessions": []
    }
    return {"roomCode": code, "status": "created"}

@router.post("/rooms/join")
async def join_room(
    roomCode: str = Form(...),
    resume: UploadFile = File(...)
):
    roomCode = roomCode.upper()
    if roomCode not in active_rooms:
        raise HTTPException(status_code=404, detail="Room not found or inactive")
    
    if not resume.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF resumes are supported")
        
    session_id = str(uuid.uuid4())
    active_rooms[roomCode]["sessions"].append(session_id)
    
    # Normally we would save and parse the PDF here using PyMuPDF
    # For now we just return the session to allow the frontend flow
    return {"sessionId": session_id, "status": "joined"}
