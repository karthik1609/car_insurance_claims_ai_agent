#!/usr/bin/env python
"""
Main application entry point
"""
import os
import logging
import logging.config
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from src.api.routes import router as main_router
from src.api.routes_testing import router as testing_router
from src.core.config import settings
from src.ocr.azure_recognizer import AzureRecognizerClient, close_azure_client

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

# Global Azure client instance - will be managed by lifespan
azure_ocr_client: Optional[AzureRecognizerClient] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage an AzureRecognizerClient instance across the application's lifespan."""
    global azure_ocr_client
    logger.info("FastAPI app starting up - initializing AzureRecognizerClient...")
    # Initialize the client upon application startup
    # The AccidentReportService will instantiate its own client when needed,
    # this lifespan event is more for a global client if we decided to make it a singleton
    # passed via dependency injection. For now, AccidentReportService creates its own.
    # If a shared client is desired, initialize it here and pass it around.
    # For simplicity with current AccidentReportService design, we might not need a global one here.
    # However, if multiple services used it, this would be the place.
    # Let's keep this for potential future refactoring or if client is heavy to init.
    # For now, we will rely on AccidentReportService creating its own.
    # No explicit global client creation here yet, but close_azure_client might be useful
    # if we had a global instance. The current structure is fine for service-level client.
    yield
    # Clean up the client when the application is shutting down
    # This is tricky if AccidentReportService creates its own instances.
    # A better pattern would be to have a single client injected.
    # For now, let's assume we might want to close a *hypothetical* global client.
    # If services manage their own, this specific close here might not be strictly necessary
    # unless the client itself holds resources that need explicit async closing even when GC'd.
    # The Azure SDK clients often benefit from explicit close.
    # Since AccidentReportService is the primary user, it could manage its client's closure
    # if it were, e.g. a singleton service. 
    # The close_azure_client function is designed for an instance, not a class.
    logger.info("FastAPI app shutting down...")
    # if azure_ocr_client:  # Example if we had a global client
    #     await close_azure_client(azure_ocr_client)
    #     logger.info("Global AzureRecognizerClient closed.")


# Create FastAPI app with lifespan manager
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include routers
app.include_router(main_router)
app.include_router(testing_router)

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