from pydantic import BaseModel


class CreateQuestionPaper(BaseModel):
    title: str
    description: str
    year: int
    month: str
    subject_id: int

class CreateIntroText(BaseModel):
    name: str
    type :str

class CreateOptions(BaseModel):
    text: str
    option_label: str
    is_correct: bool
    score: float
    feedback: str
    question_id: int