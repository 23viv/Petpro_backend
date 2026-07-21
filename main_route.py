from fastapi import FastAPI
from routes.Auth import auth_routes
from routes.Message import Message_route
from routes.Pets import Pets_routes
from routes.User import User_routes
from routes.Diet import Diet_routes

app = FastAPI(title="PetPro API", version="1.0.0")

app.include_router(auth_routes.router)
app.include_router(Message_route.router)
app.include_router(Pets_routes.router)
app.include_router(User_routes.router)
app.include_router(Diet_routes.router)
