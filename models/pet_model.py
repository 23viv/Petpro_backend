from pickle import TRUE
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from sqldatabase import Base


class Pet(Base):
    __tablename__ = "pets"

    id = Column(Integer, primary_key=True, index=True)

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    name = Column(String(100), nullable=False)

    # e.g. "dog", "cat", "bird", "other"
    pet_type = Column(String(50), nullable=False)

    # e.g. "Golden Retriever" -- optional, and only makes sense for some pet_types
    breed = Column(String(100), nullable=True)

    # optional -- not every owner knows this
    date_of_birth = Column(Date, nullable=True)

    # fallback for when date_of_birth is unknown -- owner's rough estimate in years
    approximate_age_years = Column(Integer, nullable=True)

    photo_url = Column(String(600),nullable=True)

    created_at = Column(DateTime, server_default=func.now())

    owner = relationship("User", backref="pets")