from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    tenant_code: str = Field(min_length=1, max_length=80)
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CurrentUserResponse(BaseModel):
    id: str
    tenant_id: str
    tenant_code: str
    username: str
    email: str
    role: str
