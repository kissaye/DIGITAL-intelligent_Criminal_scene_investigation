from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class UserProfile(BaseModel):
    id: int
    username: str
    display_name: str = Field(serialization_alias="displayName")
    roles: list[str]


class TokenData(BaseModel):
    access_token: str = Field(serialization_alias="accessToken")
    token_type: str = Field(serialization_alias="tokenType")
    expires_in: int = Field(serialization_alias="expiresIn")
    user: UserProfile
