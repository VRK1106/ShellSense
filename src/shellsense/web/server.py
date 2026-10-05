import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any
from src.shellsense.core.config_manager import ConfigManager
from src.shellsense.services.ai_coder import AICoder

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

class PromptRequest(BaseModel):
    prompt: str

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

class VaultCryptRequest(BaseModel):
    text: str
    password: str

# Endpoints for Vault
@app.post("/api/vault/encrypt")
def vault_encrypt(payload: VaultCryptRequest):
    from src.shellsense.services.vault_service import VaultService
    if not payload.password:
        raise HTTPException(status_code=400, detail="Master password is required")
    encrypted = VaultService.encrypt_value(payload.text, payload.password)
    return {"encrypted": encrypted}

@app.post("/api/vault/decrypt")
def vault_decrypt(payload: VaultCryptRequest):
    from src.shellsense.services.vault_service import VaultService
    if not payload.password:
        raise HTTPException(status_code=400, detail="Master password is required")
    decrypted = VaultService.decrypt_value(payload.text, payload.password)
    if decrypted is None:
        raise HTTPException(status_code=401, detail="Incorrect master password or corrupted ciphertext")
    return {"decrypted": decrypted}

# Endpoint for AI Coder
@app.post("/api/ai/code")
def ai_code(request: PromptRequest):
    result = AICoder.execute_prompt(request.prompt)
    if result.get("success"):
        return {"status": "success", "message": result.get("message")}
    raise HTTPException(status_code=500, detail=result.get("error", "AI modification failed"))

# Mount static files for the frontend
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
