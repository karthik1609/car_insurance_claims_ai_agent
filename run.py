#!/usr/bin/env python
"""
Main application entry point
"""
import os
import logging
import logging.config
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from src.api.routes import router
from src.core.config import settings

# Load environment variables
load_dotenv()

# Configure logging
logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "level": "DEBUG",
        },
        "file": {
            "formatter": "default",
            "class": "logging.FileHandler",
            "level": "INFO",
            "filename": "app.log",
            "mode": "a",
        },
    },
    "loggers": {
        "": {"handlers": ["console", "file"], "level": "INFO"},
        "src": {"handlers": ["console", "file"], "level": "INFO" if not settings.DEBUG_MODE else "DEBUG", "propagate": False},
        "uvicorn": {"handlers": ["console", "file"], "level": "INFO"},
    },
}

logging.config.dictConfig(logging_config)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include router
app.include_router(router)

# Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint"""
    logger.info("Root endpoint accessed")
    return {"message": "Car Insurance Claims AI Agent API is running"}

# Health check endpoint
@app.get("/health", include_in_schema=False)
async def health():
    """Health check endpoint"""
    logger.debug("Health check endpoint accessed")
    return {"status": "ok"}

if __name__ == "__main__":
    logger.info(f"Starting server at {settings.API_HOST}:{settings.API_PORT}")
    uvicorn.run(
        "run:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG_MODE,
    ) 