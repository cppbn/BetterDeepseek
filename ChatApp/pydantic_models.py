from pydantic import BaseModel, Field, model_validator
from typing import List, Optional
from datetime import datetime


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class SessionCreateResponse(BaseModel):
    session_id: str


class SessionInfo(BaseModel):
    session_id: str
    title: Optional[str] = None
    created_at: datetime


class MessageResponse(BaseModel):
    id: int
    seq: int
    idx: int
    role: str
    type: str  # message / reasoning / tool_call / tool_result
    content: str
    created_at: datetime


class ChatRequest(BaseModel):
    message: str = Field(..., max_length=4000)
    attachments_file_id: Optional[List[str]] = None
    model: Optional[str] = None
    enable_search: bool = Field(default=True)
    enable_code_exec: bool = Field(default=True)

    @model_validator(mode='after')
    def check_message_or_attachments(self):
        has_attachments = bool(self.attachments_file_id)
        if not has_attachments and not self.message.strip():
            raise ValueError('message is required when no attachments are provided')
        return self


class UserInfo(BaseModel):
    id: int
    username: str

class FileInfo(BaseModel):
    file_id: str
    original_filename: str
    file_size: int
    mime_type: str