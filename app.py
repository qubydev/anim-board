from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from backend.routes import router  # your API routes

app = FastAPI(title="Anim-Board API")

# --- CORS setup ---
frontend_ports = [4173, 5173, 3000]
origins = [f"http://localhost:{port}" for port in frontend_ports] + [
    f"http://127.0.0.1:{port}" for port in frontend_ports
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API routes ---
app.include_router(router, prefix="/api")

# --- Serve frontend ---
dist_path = Path(__file__).parent.parent / "frontend" / "dist"
app.mount("/static", StaticFiles(directory=dist_path / "assets"), name="static")  # optional, Vite assets

# Fallback route for SPA
@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    index_file = dist_path / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"error": "Frontend build not found"}
