import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any
from src.shellsense.core.config_manager import ConfigManager

app = FastAPI(title="ShellSense Web API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConfigData(BaseModel):
    data: Dict[str, Any]

# Endpoints for Snippets
@app.get("/api/snippets")
def get_snippets():
    return ConfigManager.get_snippets()

@app.post("/api/snippets")
def update_snippets(payload: ConfigData):
    if ConfigManager.update_snippets(payload.data):
        return {"status": "success"}
    raise HTTPException(status_code=500, detail="Failed to update snippets")

# Endpoints for Shortcuts
@app.get("/api/shortcuts")
def get_shortcuts():
    return ConfigManager.get_shortcuts()

@app.post("/api/shortcuts")
def update_shortcuts(payload: ConfigData):
    if ConfigManager.update_shortcuts(payload.data):
        return {"status": "success"}
    raise HTTPException(status_code=500, detail="Failed to update shortcuts")

# Endpoints for Commands
@app.get("/api/commands")
def get_commands():
    return ConfigManager.get_commands()

@app.post("/api/commands")
def update_commands(payload: ConfigData):
    if ConfigManager.update_commands(payload.data):
        return {"status": "success"}
    raise HTTPException(status_code=500, detail="Failed to update commands")

# Endpoints for Vault (Zero-Knowledge Architecture)
@app.post("/api/vault/encrypt")
def vault_encrypt():
    raise HTTPException(
        status_code=410,
        detail="Zero-knowledge architecture: Master passwords are never sent to the server. Encryption must be performed client-side using WebCrypto."
    )

@app.post("/api/vault/decrypt")
def vault_decrypt():
    raise HTTPException(
        status_code=410,
        detail="Zero-knowledge architecture: Master passwords are never sent to the server. Decryption must be performed client-side using WebCrypto."
    )

# Mount static files for the frontend
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
