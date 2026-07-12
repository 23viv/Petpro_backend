from pydantic import BaseModel,Field

class Pet(BaseModel):
    name: str = Field()
    age: int = Field()
    breed: str = Field()
    owner: str = Field()
    
    