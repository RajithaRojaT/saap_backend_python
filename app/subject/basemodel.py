from pydantic import BaseModel


class SubjectCreate(BaseModel):
    subject_name: str
    subject_code: str


class CreateSection(BaseModel):
    name: str
    description: str
    question_paper_id: int