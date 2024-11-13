from fastapi import FastAPI
from api.routes import router
from core.config import settings


app = FastAPI(title=settings.PROJECT_NAME)

app.include_router(router, prefix=settings.API_V1_STR)

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return {
        "error": True,
        "message": str(exc),
        "status_code": getattr(exc, "status_code", 500)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)