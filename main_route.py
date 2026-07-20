from fastapi import FastAPI
from routes.Auth import auth_routes
from routes.Message import Message_route

app = FastAPI()

app.include_router(auth_routes.router)
app.include_router(Message_route.router)
