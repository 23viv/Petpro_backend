from pydantic import BaseModel,Field

class User(BaseModel):
    username: str =  Field ()
    email: str = Field()
    password: str
