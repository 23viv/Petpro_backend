from fastapi import FastAPI
from routes.Auth import auth_routes 
app = FastAPI()

app.include_router(auth_routes.router)

