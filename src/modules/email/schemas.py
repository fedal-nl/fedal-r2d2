from pydantic import BaseModel, EmailStr, Field, model_validator


class EmailSendRequest(BaseModel):
    application: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    reply_to: EmailStr
    subject: str = Field(min_length=1, max_length=998)
    html: str | None = None
    text: str | None = None

    @model_validator(mode="after")
    def require_body(self):
        if not self.html and not self.text:
            raise ValueError("Either html or text must be provided")
        return self
