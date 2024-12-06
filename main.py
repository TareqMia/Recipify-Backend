from fastapi import FastAPI, Request
from api.routes import router
from core.config import settings
import logging

app = FastAPI(title=settings.PROJECT_NAME)

app.include_router(router, prefix=settings.API_V1_STR)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unhandled exception: {exc}")
    return {
        "error": True,
        "message": "An unexpected error occurred. Please try again later.",
        "status_code": 500
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)