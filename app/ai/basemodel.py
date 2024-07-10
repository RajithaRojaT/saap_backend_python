from typing import List
from pydantic import BaseModel


class AiPromptItem(BaseModel):
    question_id: int
    prompt_text: str
    
class CreateAiPrompt(BaseModel):
    prompts: List[AiPromptItem]

class UpdateAiPrompt(BaseModel):
    prompt_text: str

