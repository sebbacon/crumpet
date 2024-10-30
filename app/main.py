from fastapi import FastAPI
from . import database

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Welcome to the Documents API"}

# Ensure database is migrated on startup
@app.on_event("startup")
async def startup_event():
    database.migrate()
