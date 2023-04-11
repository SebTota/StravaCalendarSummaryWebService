import enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, String, Enum, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column

from backend.db.base_class import Base

if TYPE_CHECKING:
    from .strava_auth import StravaAuth  # noqa: F401


class UserStatus(str, enum.Enum):
    ACTIVE = 'ACTIVE'
    PENDING_EMAIL_VERIFICATION = 'PENDING_EMAIL_VERIFICATION'
    INACTIVE = 'INACTIVE'


class User(Base):
    id = Column(String(length=12), primary_key=True, index=True)
    first_name = Column(String(length=50), index=True, nullable=False)
    last_name = Column(String(length=50), index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    status = Column(Enum(UserStatus), nullable=False)
    is_superuser = Column(Boolean(), default=False, nullable=False)
    strava_auth = relationship("StravaAuth", back_populates="user", cascade="all, delete-orphan")