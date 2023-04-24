import datetime
from typing import Optional, List

from pydantic import BaseModel


# Shared properties
class GoogleAuthBase(BaseModel):
    token: Optional[str]
    token_uri: Optional[str]
    client_id: Optional[str]
    client_secret: Optional[str]
    expiry: Optional[datetime.datetime]
    refresh_token: Optional[str]
    scopes: Optional[list]


class GoogleAuthCreate(BaseModel):
    token: str
    token_uri: str
    client_id: str
    client_secret: str
    expiry: datetime.datetime
    refresh_token: str
    scopes: List[str]


class GoogleAuthUpdate(GoogleAuthBase):
    pass


class GoogleAuthInDBBase(GoogleAuthBase):
    id: Optional[str] = None

    class Config:
        orm_mode = True


# Additional properties to return via API
class GoogleAuth(GoogleAuthInDBBase):
    pass


# Additional properties stored in DB
class GoogleAuthInDB(GoogleAuthInDBBase):
    pass
