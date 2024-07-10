import base64
import os
import re
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException
from flask import json
from requests import Session
import requests
from app.login.auth import JWTBearer
from app.models import Question
from database import SessionLocal, get_db
from database import get_db
from sqlalchemy.orm import Session


ai_route = APIRouter(prefix="/ai")
api_key = os.getenv("OPENAIKEY")


@ai_route.put("/update_prompt")
async def update_subject(
    request: dict,
    db: Session = Depends(get_db),
    user_data: dict = Depends(JWTBearer())
):
    prompt_ids = [i["id"] for i in request["data"]]
    prompts_to_update = db.query(Question).filter(Question.id.in_(prompt_ids)).all()

    # Create a map of id to prompt for quick lookup
    prompt_map = {prompt.id: prompt for prompt in prompts_to_update}

    for i in request["data"]:
        prompt_id = i["id"]
        if prompt_id not in prompt_map:
            raise HTTPException(
                status_code=404, detail=f"Question with id {prompt_id} not found"
            )

        UpdatePrompt = prompt_map[prompt_id]
        if "prompt_text" in i and i["prompt_text"] is not None:
            UpdatePrompt.prompt_text = i["prompt_text"]

        db.commit()

    return {"data": "Updated Prompt Successfully"}



@ai_route.post("/prompt")
async def ai_model(request: Dict[str, Any], db: Session = Depends(get_db)):
    """
    Processes user input, generates a message for evaluation, interacts
    with an AI model to provide feedback, and returns the evaluation results.

    :param request: A dictionary containing questionId, questionText, answer, max_score, and images.
    :type request: dict
    :return: Evaluation results including correctness and rating.
    """
    try:
        question_id = request.get("questionId")
        question_text = request.get("questionText")
        answer = request.get("answer")
        max_score = request.get("max_score")
        images = request.get("images", [])
        if not question_text:
            question_text = "No question text found"
        question = db.query(Question).filter(Question.id == question_id).first()
        
        if question is None:
            # Handle the case where the question is not found
            message = "Question not found"
        else:
            prompt = question.prompt_text
            if prompt :
                message =  (f"This is the question: {question_text} and my answer is: {answer}."
                    "If my answer is incorrect, could you explain why and highlight the areas I need to improve? "
                    "If my answer is null, then please provide the correct answer for the question. If my answer is  partially correct, could you identify what's missing? "
                    f"Finally, please rate my answer out of {max_score}. Evaluate my answer and give the rating. The rating must be a float and should not be null. Please provide the rating for the answer."
                    "Note: I need the sections as rating, Explanation, area of improvement, correct answer and except the rating all the others I need a detailed explanation and each section should contain atleast 5 lines, Don't show the evaluation criteria marks in any section."
                    "Do not include the evaluation criteria or the marks in the correct answer."
                    f"and the criteria to evaluate my answer is: {prompt}"
                    )
            else:
                message = (
                    f"This is the question: {question_text} and the answer is: {answer}. Could you please evaluate my answer? "
                    "If it's incorrect, could you explain why and highlight the areas I need to improve? "
                    "If the answer is null, then please provide the correct answer. If it's partially correct, could you identify what's missing? "
                    f"Finally, please rate my answer out of {max_score}. The rating must be a float and should not be null. Please provide the rating for the answer."
                    "Note: I need the sections as answer_avaluation, rating, Explanation, area of improvement, correct answer and except the rating all the others I need a detailed explanation and each section should contain atleast 5lines"
                )

        # Encode all images
        encoded_images = []
        for image in images:
            if image is not None:
                encoded_images.append(encode_image(image.split("/")[-1]))

        # Prepare the payload
        messages_content = [{"type": "text", "text": message}]
        for encoded_image in encoded_images:
            if encoded_image is not None:
                messages_content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"},
                    }
                )

        payload = {
            "model": "gpt-4o",
            "messages": [
                {"role": "user", "content": messages_content},
            ],
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        response = requests.post(
            "https://api.openai.com/v1/chat/completions", headers=headers, json=payload
        )

        if response.status_code == 200:
            data = response.json()
            ai_text_data = data["choices"][0]["message"]["content"]
            
            lines = ai_text_data.split('\n')
            lines = [line.strip() for line in lines if line.strip()]  # Remove empty lines
            
            rating_variations = [
                "### Rating", "### rating", "### Ratings", "### ratings","**Rating:**", "**rating:**"
                "###Rating", "###rating", "### Total Rating", "### Overall Rating"
            ]
            
            content = []
            start_collecting = False

            for line in lines:
                if start_collecting:
                    if any(line.startswith(variation) for variation in rating_variations):
                        break
                    content.append(line)
                if any(line.startswith(variation) for variation in rating_variations):
                    start_collecting = True
            
            if not content:
                    rating =0.0
            rating_content = "".join(content)
            
            rating_match = re.search(r'\d+(\.\d+)?', rating_content)
            if rating_match:
                rating = float(rating_match.group()) if '.' in rating_match.group() else int(rating_match.group())
            else:
                rating = 0
            evaluation = ai_text_data
            return {
                "question_id": question_id,
                "evaluation": {
                    "correctness": evaluation,
                    "rating": rating
                }
            }
        else:
            raise Exception(f"Error: API request failed with status code {response.status_code}")
    except Exception as e:
        return {"detail": f"An unexpected error occurred: {str(e)}"}

def encode_image(image):
    image_path = os.path.join("uploads", image)
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def aicall(request):
    """
    Processes user input, generates a message for evaluation, interacts
    with an AI model to provide feedback, and returns the evaluation results.

    :param request: A dictionary containing questionId, questionText, answer, max_score, and images.
    :type request: dict
    :return: Evaluation results including correctness and rating.
    """
    try:
        db = SessionLocal()
        question_ids = []  
        question_ids = [item.get("question_id") for item in request]
        questions = db.query(Question).filter(Question.id.in_(question_ids)).all()
        prompt_dict = {q.id: q.prompt_text for q in questions}

        for item in request:
            question_id = item.get("question_id")
            item['evaluation_criteria'] = prompt_dict.get(question_id)
        message = (
            f"{request}, The following are questions along with their provided answers, scores, and evaluation_criteria where applicable. "
            "Please evaluate each answer based on the provided evaluation_criteria. If no evaluation_criteria is provided for a question, evaluation should not consider a evaluation_criteria. "
            "If my answer is incorrect, explain why and highlight areas for improvement. "
            "If my answer is partially correct, identify the missing components. Finally, rate each answer out of {score} provided. "
            "The rating must be a non-null float; if the answer is null, rate it as 0."
            "*Note: The response structure should include: Area of Focus, Answer Evaluation, Rating, Explanation, Area of Improvement, correct answer for the question, Don't show the marks from evaluation criteria in correct answer, answer evaluation, explanation. "
            "Except for the rating, all other sections (Explanation, Answer Evaluation, Area of Focus) require a detailed explanation. "
            "Provide at least 3 paragraphs of explanation for each answer and area evaluation, covering areas such as context, correctness, and relevance to the evaluation_criteria if applicable and give the correct answer for the question with a paragraph"
            "The Area of Improvement should list at least 5 points. "
            "The Area of Focus should span 5 paragraphs, focusing on improving the quality of my answer based on the provided response."
            "Provide the rating for each answer in a valid JSON format without explicitly mentioning 'json'."
            "The response should be a valid json format and make this as a valid json not a string"
            "Ensure the generated responses in the specified JSON format: [{question_id, explanation, answer_evaluation, area_of_focus, rating, area_of_improvement, correct_answer}, {}]."
            "Do not include the evaluation criteria or the marks in the correct answer."
        )

        payload = {
            "model": "gpt-4o",
            "messages": [
                {"role": "user", "content": message},
            ],
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        response = requests.post(
            "https://api.openai.com/v1/chat/completions", headers=headers, json=payload
        )
       
               # newdata = extract_info(subdata)
        

        if response.status_code == 200:
            data = response.json()
            subdata = data["choices"][0]["message"]["content"]
            if "```json" in subdata:
                subdata = subdata.replace("json", "")
                subdata = subdata.replace("```", "") 
            result = json.loads(subdata)
            return result

        else:
            raise Exception(
                f"Error: API request failed with status code {response.content}"
            )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))



