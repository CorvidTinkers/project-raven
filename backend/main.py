import os
import logging
from dotenv import load_dotenv

# Load environment variables FIRST before any other imports
load_dotenv(dotenv_path="../.env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.websocket import router as websocket_router
from api.routes import router as http_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Project Raven Backend")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(http_router, prefix="/api")
app.include_router(websocket_router)

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Project Raven Backend is running"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
