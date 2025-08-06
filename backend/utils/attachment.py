from pydantic import BaseModel


class ClientAttachment(BaseModel):
    name: str
    contentType: str
    url: str


class Attachment(BaseModel):
    name: str
    type: str
    content: str
