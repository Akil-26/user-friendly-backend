from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from .database import Base, engine
from .routers import auth, news, chat

Base.metadata.create_all(bind=engine)

app = FastAPI(title="User Friendly API", version="1.0")

# CORS — allows Flutter to call this API from anywhere
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(news.router)
app.include_router(chat.router)

@app.get("/")
def root():
    return {"message": "User Friendly API is running 🚀"}

# Fix Swagger to show clean Bearer token input
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(title="User Friendly API", version="1.0", routes=app.routes)
    schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    for path in schema["paths"].values():
        for method in path.values():
            method["security"] = [{"BearerAuth": []}]
    app.openapi_schema = schema
    return schema

app.openapi = custom_openapi