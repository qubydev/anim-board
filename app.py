from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
from routes import router

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
dist_path = Path(__file__).parent / "frontend" / "dist"
app.mount("/static", StaticFiles(directory=dist_path / "assets"), name="static")

# --- SPA fallback ---
@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    index_file = dist_path / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"error": "Frontend build not found"}
    )

# --- Global exception handler ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Optionally log the exception here
    print(f"Unhandled error: {exc}")  # for server logs
    
    # Return JSON with 500 status
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": str(exc)}
    )

# --- Optional: HTTPException handler (clean JSON) ---
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

# --- Run server ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)