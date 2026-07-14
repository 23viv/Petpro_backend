from datetime import date
from pydantic import BaseModel, computed_field


class CreatePetRequest(BaseModel):
    name: str
    pet_type: str                       # "dog", "cat", "other", etc.
    breed: str | None = None            # "Golden Retriever", "German Shepherd", etc.
    date_of_birth: date | None = None
    approximate_age_years: int | None = None  # only used if date_of_birth is unknown


class PetOut(BaseModel):
    id: int
    name: str
    pet_type: str
    breed: str | None
    date_of_birth: date | None
    approximate_age_years: int | None
    photo_url: str | None

    @computed_field
    @property
    def age_years(self) -> int | None:
        if self.date_of_birth:
            today = date.today()
            years = today.year - self.date_of_birth.year
            # subtract 1 if birthday hasn't happened yet this year
            had_birthday = (today.month, today.day) >= (self.date_of_birth.month, self.date_of_birth.day)
            return years if had_birthday else years - 1
        return self.approximate_age_years  # fall back to the owner's estimate

    class Config:
        from_attributes = True