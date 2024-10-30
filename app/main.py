from fastapi import FastAPI
from . import database
from . import models

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Welcome to the Documents API"}

@app.post("/api/v1/documents", response_model=models.Document)
async def create_document(document: models.DocumentCreate):
    return database.create_document(
        title=document.title,
        description=document.description,
        content=document.content,
        tags=document.tags
    )

# Ensure database is migrated on startup
@app.on_event("startup")
async def startup_event():
    database.migrate()
