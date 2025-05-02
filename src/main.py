"""
Car Insurance Claims AI Agent - Main Application
"""
import os
from fastapi import FastAPI, Depends
from dotenv import load_dotenv

from src.api.routes import router as api_router
from src.core.config import settings

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Car Insurance Claims AI Agent",
    description="API for assessing car damage and estimating repair costs",
    version="1.0.0",
)

# Include routers
app.include_router(api_router, prefix="/api/v1")

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint returning API information"""
    return {
        "message": "Car Insurance Claims AI Agent API",
        "version": "1.0.0",
        "docs_url": "/docs",
    }

if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    debug = os.getenv("DEBUG_MODE", "true").lower() == "true"
    
    uvicorn.run("src.main:app", host=host, port=port, reload=debug) 