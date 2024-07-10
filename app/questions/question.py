from datetime import datetime, date
import io
import json
import os
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.ai.api import aicall
from app.models import (
    PaymentHistory,
    QuestionPaper,
    QuestionType,
    Section,
    Question,
    Options,
    User,
    UserResponse,
)
from app.params import DELETED, ESSAY_QUESTION_TYPE_ID, INITIAL_SCORE, OPTION_SCORE
from app.login.auth import JWTBearer
from app.models import (
    QuestionPaper,
    QuestionType,
    Section,
    Question,
    Options,
    Subject,
    UserResponse,
)
from app.params import DELETED, ESSAY_QUESTION_TYPE_ID
from database import get_db
from starlette import status
from typing import Any, Dict, List
from bs4 import BeautifulSoup
import base64
import requests
import json
from PIL import Image
import re

question_route = APIRouter(prefix="/questions", tags=["Questions"])
api_key = os.getenv("OPENAIKEY")
BASE_URL = os.getenv("DOMAIN_URL")


@question_route.get("/")
def get_questions_with_options(
    paper_id: int,
    mode: str,
    subject_id: int,
    db: Session = Depends(get_db),
    user_data: dict = Depends(JWTBearer()),
):
    """

    The function `get_questions_with_options` retrieves questions with options and subquestions based on
    provided criteria from a database and organizes the data into a structured format.

    :param paper_id: The `paper_id` parameter in the `get_questions_with_options` function represents
    the unique identifier of a question paper for which you want to retrieve questions with options.
    This parameter is used to filter the query results based on the specified question paper
    :type paper_id: int
    :param subject_id: The `subject_id` parameter in the `get_questions_with_options` function is used
    to filter questions based on the subject to which they belong. This parameter helps in retrieving
    questions that are specifically related to a particular subject
    :type subject_id: int
    :param introtext_id: The `introtext_id` parameter in the `get_questions_with_options` function
    represents the ID of the introductory text associated with the questions. This function retrieves
    questions along with their options and subquestions based on the provided criteria such as
    `paper_id`, `subject_id`, and `introtext_id`
    :type introtext_id: int
    :param db: The function `get_questions_with_options` retrieves questions with their options from a
    database based on the provided criteria. Here's a breakdown of the parameters used in the function:
    :type db: Session
    :return: The function `get_questions_with_options` returns a list of dictionaries containing
    information about question papers, sections, questions, options, and subquestions based on the
    provided criteria such as `paper_id`, `subject_id`, and `introtext_id`. The data structure includes
    details like paper ID, paper name, year, section name, section title, question ID, question text,
    question type, options for
    """
    data = (
        db.query(QuestionPaper, Section, Question, Options)
        .join(Section, QuestionPaper.id == Section.question_paper_id)
        .join(Question, Section.id == Question.section_id)
        .outerjoin(Options, Question.id == Options.question_id)
        .filter(
            QuestionPaper.id == paper_id,
            Question.subject_id == subject_id,
            Question.deleted == DELETED,
            Question.parent_id == None,
            QuestionPaper.deleted == DELETED,
        )
        .all()
    )
    user_id = user_data["id"]
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        response = JSONResponse(
            content={
                "success": False,
                "message": "User not found",
                "status": status.HTTP_404_NOT_FOUND,
                "payment_status": False,
            }
        )
        response.status_code = status.HTTP_404_NOT_FOUND
        return response
    # Added for free subscription 30days
    created_at = user.created_at
    current_date = datetime.now()
    if (current_date - created_at).days > 30:
        if mode != "view":
            payment_record = (
                db.query(PaymentHistory).filter_by(created_by_id=user_id).first()
            )
            if not payment_record:
                response = JSONResponse(
                    content={
                        "success": False,
                        "message": "Unlock the assessment by subscribing",
                        "status": status.HTTP_404_NOT_FOUND,
                        "payment_status": True,
                    }
                )
                response.status_code = status.HTTP_404_NOT_FOUND
                return response

            if payment_record.next_payment_date < datetime.now().date():
                response = JSONResponse(
                    content={
                        "success": False,
                        "message": "Renew your subscription to unlock the assessment",
                        "status": status.HTTP_404_NOT_FOUND,
                        "payment_status": True,
                    }
                )
                response.status_code = status.HTTP_404_NOT_FOUND
                return response

    if not data:
        db.close()
        response = JSONResponse(
            content={
                "success": False,
                "message": "NO QUESTION FOUND FOR THE PROVIDED CRITERIA.",
                "status": status.HTTP_404_NOT_FOUND,
                "payment_status": False,
            }
        )
        response.status_code = status.HTTP_404_NOT_FOUND
        return response

    paper_sections = {}

    subquestions_dict = {}
    question_ids = [question.id for _, _, question, _ in data]
    subquestions = db.query(Question).filter(Question.parent_id.in_(question_ids)).all()
    options = (
        db.query(Options)
        .filter(Options.question_id.in_([q.id for q in subquestions]))
        .all()
    )

    for subquestion in subquestions:
        subquestions_dict.setdefault(subquestion.parent_id, []).append(subquestion)

    options_dict = {}
    for option in options:
        options_dict.setdefault(option.question_id, []).append(option)

    # Building the data structure
    for paper, section, question, option in data:
        if paper.id not in paper_sections:
            paper_sections[paper.id] = {"paper_info": paper, "sections": {}}
        if section.id not in paper_sections[paper.id]["sections"]:
            paper_sections[paper.id]["sections"][section.id] = {
                "section_info": section,
                "questions": {},
            }
        if (
            question.id
            not in paper_sections[paper.id]["sections"][section.id]["questions"]
        ):
            paper_sections[paper.id]["sections"][section.id]["questions"][
                question.id
            ] = {"question_info": question, "options": [], "sub_questions": []}
        # if option is not None:
        #     paper_sections[paper.id]["sections"][section.id]["questions"][question.id]["options"].append({
        #         "id": option.id,
        #         "label": option.text,
        #         "option_label":option.option_label,
        #         "is_answer": 1 if option.is_correct else 0
        #     })

        if option is not None:
            option_data = {
                "id": option.id,
                "label": option.text,
                "option_label": option.option_label,
            }
            if mode == "instant":
                option_data["is_answer"] = 1 if option.is_correct else 0
            paper_sections[paper.id]["sections"][section.id]["questions"][question.id][
                "options"
            ].append(option_data)

        # Using pre-fetched subquestions and options
        subquestions_data = []
        subqs = subquestions_dict.get(question.id, [])
        for subquestion in subqs:
            subquestion_options = options_dict.get(subquestion.id, [])
            subquestions_data.append(
                {
                    "question_id": subquestion.id,
                    # "is_first":subquestion.order,
                    "question": subquestion.question_text,
                    "source_text": subquestion.source_text,
                    "score": subquestion.mark,
                    "sub_question_label": subquestion.subquestion_label,
                    "question_type": subquestion.question_type_id,
                    "options": [
                        {
                            "id": opt.id,
                            "label": opt.text,
                            "option_label": opt.option_label,
                            "is_answer": 1 if opt.is_correct else 0,
                        }
                        for opt in subquestion_options
                    ],
                }
            )
        paper_sections[paper.id]["sections"][section.id]["questions"][question.id][
            "subquestions"
        ] = subquestions_data

    # Formatting the result
    paper_sections_list = [
        {
            "paper_id": paper_id,
            "paper_name": paper_data["paper_info"].assessment_specification,
            "year": paper_data["paper_info"].year,
            "sections": [
                {
                    "name": section_data["section_info"].name,
                    "title": [section_data["section_info"].description],
                    "questions": [
                        {
                            "question_id": question_id,
                            "question": question_data["question_info"].question_text,
                            "score": question_data["question_info"].mark,
                            "source_text": question_data["question_info"].source_text,
                            "question_number": question_data[
                                "question_info"
                            ].question_number,
                            "question_type": question_data[
                                "question_info"
                            ].question_type_id,
                            "options": question_data["options"],
                            "sub_questions": question_data["subquestions"],
                        }
                        for question_id, question_data in section_data[
                            "questions"
                        ].items()
                    ],
                }
                for section_id, section_data in paper_data["sections"].items()
            ],
        }
        for paper_id, paper_data in paper_sections.items()
    ]
    db.close()
    return paper_sections_list


def get_rating(response):
    """
    The function `get_rating` retrieves the rating value from a dictionary-like response using different
    possible keys.

    :param response: The `get_rating` function takes a dictionary `response` as input and searches for a
    key related to ratings within the dictionary. It checks for keys like "rating", "Rating", "ratings",
    or "Ratings" and returns the value associated with the first key it finds. If none of
    :return: The `get_rating` function is designed to extract the rating value from a dictionary-like
    `response` object. It checks for keys such as "rating", "Rating", "ratings", or "Ratings" in the
    `response` object and returns the corresponding value if found. If none of these keys are present in
    the `response` object, it returns 0.
    """
    possible_keys = ["rating", "Rating", "ratings", "Ratings", "score", "Score"]
    for key in possible_keys:
        if key in response:
            return response[key]
    return 0


@question_route.post("/response")
def create_user_response(
    create_response: dict,
    db: Session = Depends(get_db),
    user_data: dict = Depends(JWTBearer()),
):
    """
    This endpoint creates a user response record in the database based on the provided input data.

    :param create_response: The `create_response` parameter is a dictionary containing the user's response data.
    :type create_response: dict
    :param db: The `db` parameter is an instance of the database session used to interact with the database.
    :type db: Session
    :return: A JSON response with a message indicating the successful addition of the user response and the response ID.
    """
    try:
        # user_id = user_data["id"]
        user_response_json = create_response.get("user_response", {})
        subject_id = user_response_json.get("subject_id")
        user_id = user_response_json.get("user_id")
        question_paper_id = user_response_json.get("paper_id")
        year = user_response_json.get("year")

        responses = user_response_json.get("responses", [])
        time_taken = user_response_json.get("time_taken", 0)

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            response = JSONResponse(
                content={
                    "success": False,
                    "message": f"User ID {user_id} not found.",
                    "status": status.HTTP_404_NOT_FOUND,
                }
            )
            response.status_code = status.HTTP_404_NOT_FOUND
            return response

        question_paper = (
            db.query(QuestionPaper)
            .filter(QuestionPaper.id == question_paper_id)
            .first()
        )
        if not question_paper:
            response = JSONResponse(
                content={
                    "success": False,
                    "message": f"Question Paper ID {question_paper_id} not found.",
                    "status": status.HTTP_404_NOT_FOUND,
                }
            )
            response.status_code = status.HTTP_404_NOT_FOUND
            return response

        subject = db.query(Subject).filter(Subject.id == subject_id).first()
        if not subject:
            response = JSONResponse(
                content={
                    "success": False,
                    "message": f"Subject ID {subject_id} not found.",
                    "status": status.HTTP_404_NOT_FOUND,
                }
            )
            response.status_code = status.HTTP_404_NOT_FOUND
            return response

        question_ids = [response["id"] for response in responses]

        questions = db.query(Question).filter(Question.id.in_(question_ids)).all()
        question_types = db.query(QuestionType).all()
        options = db.query(Options).all()

        question_dict = {question.id: question for question in questions}
        question_type_dict = {qt.id: qt for qt in question_types}
        option_dict = {option.id: option for option in options}

        total_score = INITIAL_SCORE
        for response in responses:
            question_id = response["id"]
            answer = response["answer"]

            question = question_dict.get(question_id)
            if not question:
                db.close()
                response = JSONResponse(
                    content={
                        "success": False,
                        "message": f"Question ID {question_id} not found",
                        "status": status.HTTP_404_NOT_FOUND,
                    }
                )
                response.status_code = status.HTTP_404_NOT_FOUND
                return response
            question_type = question_type_dict.get(question.question_type_id)
            if not question_type:
                db.close()
                response = JSONResponse(
                    content={
                        "success": False,
                        "message": f"QuestionType ID {question.question_type_id} not found",
                        "status": status.HTTP_404_NOT_FOUND,
                    }
                )
                response.status_code = status.HTTP_404_NOT_FOUND
                return response

            if question.question_type_id == ESSAY_QUESTION_TYPE_ID:
                rating = get_rating(response)
                if rating is None:
                    rating = 0
                elif isinstance(rating, str):
                    try:
                        rating = float(rating)
                    except ValueError:
                        db.close()
                        response = JSONResponse(
                            content={
                                "success": False,
                                "message": f"Rating {rating} is not a valid number",
                                "status": status.HTTP_400_BAD_REQUEST,
                            }
                        )
                        response.status_code = status.HTTP_400_BAD_REQUEST
                        return response
                total_score += rating
            else:
                try:
                    option_id = int(answer)
                except ValueError:
                    db.close()
                    response = JSONResponse(
                        content={
                            "success": False,
                            "message": f"Answer {answer} is not a valid option ID",
                            "status": status.HTTP_400_BAD_REQUEST,
                        }
                    )
                    response.status_code = status.HTTP_400_BAD_REQUEST
                    return response
                option = option_dict.get(option_id)
                if not option:
                    db.close()
                    response = JSONResponse(
                        content={
                            "success": False,
                            "message": f"Option ID {option_id} not found",
                            "status": status.HTTP_404_NOT_FOUND,
                        }
                    )
                    response.status_code = status.HTTP_404_NOT_FOUND
                    return response

                if option.is_correct:
                    total_score += OPTION_SCORE

        user_response = UserResponse(
            subject_id=subject_id,
            user_id=user_id,
            question_paper_id=question_paper_id,
            user_response=json.dumps(user_response_json),
            year=year,
            created_by_id=user_id,
            total_score=total_score,
        )

        db.add(user_response)
        db.commit()
        db.refresh(user_response)
        db.close()
        return {
            "Message": "User Response Added Successfully",
            "id": user_response.id,
            "totalscore": total_score,
        }

    except Exception as e:
        db.rollback()
        print(str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


def transform_image_urls(html_content: str) -> str:
    """
    The function `transform_image_urls` uses BeautifulSoup to update image URLs in HTML content by
    prepending a base URL if the URL does not already start with 'http'.

    :param html_content: The `html_content` parameter is a string that represents the HTML content of a
    web page
    :type html_content: str
    :return: The function `transform_image_urls` takes an HTML content as input, finds all image tags
    (`<img>`) in the content, and checks if the `src` attribute of the image tag does not start with
    'http'. If it doesn't start with 'http', it appends the `BASE_URL` to the `src` attribute value.
    Finally, it returns the modified HTML content with
    """
    soup = BeautifulSoup(html_content, "html.parser")
    for img in soup.find_all("img"):
        if img.get("src") and not img["src"].startswith("http"):
            img["src"] = BASE_URL + img["src"]
    return str(soup)


def extract_image_urls(
    html_content: str,
) -> List[str]:
    """
    Extracts image URLs from HTML content and returns them in a list.

    :param html_content: The HTML content to parse
    :type html_content: str
    :param base_url: The base URL to use for relative image URLs
    :type base_url: str
    :return: A list of image URLs extracted from the HTML content
    :rtype: List[str]
    """
    soup = BeautifulSoup(html_content, "html.parser")
    image_urls = []

    for img in soup.find_all("img"):
        img_url = img.get("src")
        if img_url:
            img_url = img_url.replace("\\", "/")
            image_urls.append(img_url)
            return image_urls


@question_route.post("/response-exam-mode")
async def create_user_response(
    create_response: dict,
    db: Session = Depends(get_db),
    #    user_data: dict = Depends(JWTBearer())
):
    """
    This function creates a user response record in a database based on the provided input data,
    retrieves question types for each question based on their IDs, evaluates essay-type questions
    using an AI model, and calculates the score for all questions.

    :param create_response: Dictionary containing the data sent in the request body when making a POST
                            request to the `/response-exam-mode` endpoint.
    :param db: Database session instance used to interact with the database.
    :return: A JSON response with a message indicating the success of the operation and the user response ID.
    """
    try:
        user_response_json = create_response.get("user_response", {})
        subject_id = user_response_json.get("subject_id")
        user_id = user_response_json.get("user_id")
        question_paper_id = user_response_json.get("paper_id")
        year = user_response_json.get("year")
        responses = user_response_json.get("responses", [])
        time_taken = user_response_json.get("time_taken", 0)

        question_ids = [response.get("id") for response in responses]
        questions = db.query(Question).filter(Question.id.in_(question_ids)).all()
        question_type_dict = {q.id: q.question_type_id for q in questions}
        question_score_dict = {q.id: q.mark for q in questions}
        options_dict = {option.id: option for option in db.query(Options).all()}

        parent_question_ids = [q.parent_id for q in questions if q.parent_id]
        parent_questions = (
            db.query(Question).filter(Question.id.in_(parent_question_ids)).all()
        )
        parent_question_cache = {pq.id: pq for pq in parent_questions}

        detailed_responses: List[Dict[str, Any]] = []
        essay_evaluations = []
        total_score = 0

        for response in responses:
            question_id = response.get("id")
            answer = response.get("answer")
            # If answer is empty or None, replace with default message
            if not answer:
                answer = "No answer was given"

            question = next((q for q in questions if q.id == question_id), None)
            if not question:
                db.close()
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Question ID {question_id} not found.",
                )

            detailed_response = {
                "id": question_id,
                "answer": answer,
                "question_type": question.question_type_id,
            }

            if question.question_type_id == ESSAY_QUESTION_TYPE_ID:
                max_score = question_score_dict.get(question_id, 0)
                parent_question = None
                if question.parent_id:
                    parent_question = parent_question_cache.get(question.parent_id)
                    if not parent_question:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Parent Question ID {question.parent_id} not found.",
                        )

                    combined_text = (
                        f"{parent_question.question_text} {question.question_text}"
                    )
                    combined_text = transform_image_urls(combined_text)
                    base64_images = extract_image_urls(combined_text)
                    soup = BeautifulSoup(combined_text, "html.parser")
                    combined_text_plain = soup.get_text()
                    request = {
                        "question_id": question_id,
                        "question": combined_text_plain,
                        "answer": answer,
                        "score": max_score,
                        "images": base64_images,
                    }
                    essay_evaluations.append(request)
                    detailed_response["question_text"] = combined_text
                else:
                    question_text = transform_image_urls(question.question_text)
                    base64_images = extract_image_urls(question_text)
                    # print(base64_images)
                    soup = BeautifulSoup(question_text, "html.parser")
                    question_text_plain = soup.get_text()
                    request = {
                        "question_id": question_id,
                        "question": question_text_plain,
                        "answer": answer,
                        "score": max_score,
                        "images": base64_images,
                    }
                    essay_evaluations.append(request)

                    detailed_response["question_text"] = question_text
            else:

                if answer == "No answer was given":
                    detailed_response["score"] = 0
                else:
                    option_id = None
                    if answer is not None:
                        if isinstance(answer, str) and answer.isdigit():
                            option_id = int(answer)
                        elif (
                            isinstance(answer, list)
                            and len(answer) > 0
                            and answer[0].isdigit()
                        ):
                            option_id = int(answer[0])
                        else:
                            raise ValueError(
                                "Invalid answer format. Expected numeric string or list of numeric strings."
                            )
                    else:
                        raise ValueError("Answer is None.")

                    option = options_dict.get(option_id)
                    if option:
                        is_correct = option.is_correct
                        score = 1 if is_correct else 0
                        total_score += score
                        detailed_response["score"] = score
                    else:
                        detailed_response["score"] = 0

            option_scores = total_score

            detailed_responses.append(detailed_response)

        airesponse = aicall(essay_evaluations)
        total_rating = sum(evaluation["rating"] for evaluation in airesponse)
        option_scores += total_rating

        possible_keys = ["rating", "ratings", "mark", "marks", "score", "scores"]

        user_response = UserResponse(
            subject_id=subject_id,
            user_id=user_id,
            question_paper_id=question_paper_id,
            user_response=json.dumps(user_response_json, ensure_ascii=False),
            ai_response=airesponse,
            year=year,
            created_by_id=1,
            total_score=option_scores,
        )
        db.add(user_response)
        db.commit()
        db.refresh(user_response)

        db.close()
        return {
            "Message": "User Response Added Successfully",
            "id": user_response.id,
            "total_score": option_scores,
        }
    except Exception as e:
        db.rollback()
        db.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@question_route.get("/alluser")
def get_user_responses(
    db: Session = Depends(get_db),
    user_data: dict = Depends(JWTBearer()),
):
    """
    The function retrieves all user responses from the database and processes them before returning the
    results.

    :param db: The `db` parameter in the `get_user_responses` function is of type `Session`, which is a
    database session object. It is used to interact with the database and perform queries to retrieve
    user responses stored in the database. The `Session` object is typically created using an ORM
    (Object-
    :type db: Session
    :return: The code is defining a route `/alluser` with a GET method that retrieves all user responses
    from the database. It then processes each user response by converting the `user_response` field from
    JSON to a Python dictionary and modifies the structure of the responses by excluding the
    "sub_questions" key from each response item. Finally, it returns the processed user responses. If
    any exception occurs during this process,
    """
    try:
        user_responses = db.query(UserResponse).all()

        for response in user_responses:
            response.user_response = json.loads(response.user_response)
            response.user_response["responses"] = [
                {k: v for k, v in response_item.items() if k != "sub_questions"}
                for response_item in response.user_response.get("responses", [])
            ]
        db.close()
        return user_responses
    except Exception as e:
        db.close()
        raise HTTPException(status_code=500, detail=str(e))


@question_route.get("/result/{user_response_id}")
def get_question_options_text(
    user_response_id: int,
    db: Session = Depends(get_db),
    user_data: dict = Depends(JWTBearer()),
):
    """
    The function `get_question_options_text` calculates and returns statistics based on user responses
    to questions in a question paper.

    :param user_id: The `user_id` parameter represents the unique identifier of the user for whom you
    want to retrieve question options text. This identifier is used to filter the user responses in the
    database
    :type user_id: int
    :param question_paper_id: The `question_paper_id` parameter in the `get_question_options_text`
    function represents the unique identifier of the question paper for which you want to retrieve
    question options text and related statistics. This parameter helps in filtering the user responses
    and question options specific to a particular question paper
    :type question_paper_id: int
    :param subject_id: The `subject_id` parameter in the `get_question_options_text` function represents
    the unique identifier for the subject for which the question options are being retrieved. It is used
    to filter the user responses and question options related to a specific subject in the database
    :type subject_id: int
    :param db: The `db` parameter in the `get_question_options_text` function is a SQLAlchemy Session
    object that is used to interact with the database. It is passed as a dependency using
    `Depends(get_db)`, where `get_db` is likely a function that provides access to the database session
    within the
    :type db: Session
    :return: The function `get_question_options_text` returns a dictionary containing the following
    information:
    - "totalAttempted": Total number of questions attempted by the user
    - "correctAnswers": Total number of correct answers given by the user
    - "wrongAnswers": Total number of incorrect answers given by the user
    - "totalScore": Total score achieved by the user based on correct answers
    - "time
    """
    try:
        user_responses = (
            db.query(UserResponse).filter(UserResponse.id == user_response_id).all()
        )
        if not user_responses:
            raise HTTPException(status_code=404, detail="User response not found")

        response_list = []
        question_stats = {}
        time_taken = 0

        all_options = db.query(Options).all()
        for user_response in user_responses:
            response_json = json.loads(user_response.user_response)
            time_taken = response_json.get("time")

        for question_response in response_json.get("responses", []):
            question_id = question_response.get("question_id")
            answer = question_response.get("answer")
            option_id = None
            if answer is not None and answer.isdigit():
                option_id = int(answer)

                if question_id not in question_stats:
                    question_stats[question_id] = {
                        "total": 0,
                        "correct": 0,
                        "incorrect": 0,
                    }

                option = next((opt for opt in all_options if opt.id == option_id), None)
                if option:
                    is_correct = option.is_correct
                    score = 1 if is_correct else 0
                    response_list.append({"question_id": question_id, "score": score})
                    question_stats[question_id]["total"] += 1
                    if is_correct:
                        question_stats[question_id]["correct"] += 1
                    else:
                        question_stats[question_id]["incorrect"] += 1
                else:
                    response_list.append(
                        {
                            "question_id": question_id,
                            "option_id": option_id,
                            "is_correct": None,
                            "score": 0,
                        }
                    )

        total_score = sum(stats["correct"] for stats in question_stats.values())
        total_question_id = len(response_json.get("responses", []))
        total_correct_answer = sum(
            stats["correct"] for stats in question_stats.values()
        )
        total_wrong_answer = sum(
            stats["incorrect"] for stats in question_stats.values()
        )
        user_response.total_score = total_score
        db.commit()
        db.close()

        return {
            "totalAttempted": total_question_id,
            "correctAnswers": total_correct_answer,
            "wrongAnswers": total_wrong_answer,
            "totalScore": total_score,
            "timeTaken": time_taken,
            "user_response_id": user_response_id,
        }

    except Exception as e:
        db.close()
        raise HTTPException(status_code=500, detail=str(e))


@question_route.get("/resultview/{user_response_id}")
def get_response_result_view(
    user_response_id: int,
    db: Session = Depends(get_db),
    user_data: dict = Depends(JWTBearer()),
):
    """
    Retrieve a list of question IDs, answers, scores for each question, and total score for a specific user and question paper.

    :param user_response_id: The ID of the user response.
    :type user_response_id: int
    :param mode: The mode of the view ("instant" or "exam").
    :type mode: str
    :param db: The database session dependency.
    :type db: Session
    :return: A dictionary containing answers, question paper ID, scores for each question, and total score.
    :rtype: Dict[str, Any]
    """
    try:
        user_response = (
            db.query(UserResponse).filter(UserResponse.id == user_response_id).first()
        )
        if not user_response:
            response = JSONResponse(
                content={
                    "success": False,
                    "message": f"User response not found {user_response_id}",
                    "status": status.HTTP_404_NOT_FOUND,
                }
            )
            response.status_code = status.HTTP_404_NOT_FOUND
            return response

        if isinstance(user_response.user_response, str):
            response_json = json.loads(user_response.user_response)
        else:
            response_json = user_response.user_response

        question_paper_id = response_json.get("paper_id")
        mode = response_json.get("exam_mode")
        response_list = []
        all_questions = db.query(Question).all()
        question_dict = {q.id: q for q in all_questions}
        all_options = db.query(Options).all()
        options_dict = {}
        for option in all_options:
            if option.question_id not in options_dict:
                options_dict[option.question_id] = []
            options_dict[option.question_id].append(option)

        if mode == "exam":
            if isinstance(user_response.ai_response, str):
                ai_response = json.loads(user_response.ai_response)
            else:
                ai_response = (
                    user_response.ai_response if user_response.ai_response else []
                )

            for question_response in response_json.get("responses", []):
                question_id = question_response.get("id")
                user_answer = question_response.get("answer")
                question = question_dict.get(question_id)
                get_question = question_dict.get(question_id)
                mark = get_question.mark
                if not question:
                    continue

                question_type_id = question.question_type_id
                if question_type_id == ESSAY_QUESTION_TYPE_ID:
                    evaluation = next(
                        (
                            item
                            for item in ai_response
                            if item.get("question_id") == question_id
                        ),
                        {},
                    )
                    correct_answer = None
                    explanation = evaluation.get(
                        "explanation", "Your answer does not have any explanation"
                    )
                    answer_evaluation = evaluation.get(
                        "answer_evaluation",
                        "Your answer does not have any answer evaluation",
                    )
                    area_of_improvement = evaluation.get(
                        "area_of_improvement",
                        ["There is no area of improvement for your answer"],
                    )
                    area_of_focus = evaluation.get(
                        "area_of_focus",
                        "Your answer does not have any area to be focused",
                    )
                    correct_answer = evaluation.get("correct_answer", None)

                    rating = evaluation.get("rating", None)
                    area_of_improvement_str = "\n\n".join(area_of_improvement)
                    feedback = {
                        "explanation": explanation,
                        "correctness": f"\n\n{explanation}\n\n<b>Answer Evaluation:</b>\n\n{answer_evaluation}\n\n<b>Area of Improvement:</b>\n\n{area_of_improvement_str}\n\n<b>Area of Focus</b>\n\n{area_of_focus}\n\n<b>Rating:</b> {rating}\n\n<b>Correct Answer:</b>{correct_answer}",
                    }
                else:
                    correct_option = next(
                        (
                            opt
                            for opt in options_dict.get(question_id, [])
                            if opt.is_correct
                        ),
                        None,
                    )
                    correct_answer = correct_option.id if correct_option else None
                    feedback = None
                
                    if user_answer is not None:
                        try:
                            if int(user_answer) == correct_answer:
                                rating = 1
                            else:
                                rating = 0
                        except ValueError:
                            rating = 0
                    else:
                        rating = 0
                response_list.append(
                    {
                        "id": question_id,
                        "response": user_answer,
                        "rating": rating,
                        "correct_answer": correct_answer,
                        "mark": mark,
                        "feedback": feedback,
                    }
                )

        elif mode == "instant":
            correct_answers = {}
            options = db.query(Options).filter(Options.is_correct == True).all()
            for option in options:
                correct_answers.setdefault(option.question_id, []).append(option.id)

            for question_response in response_json.get("responses", []):
                question_id = question_response.get("id")
                option_id = question_response.get("answer")
                get_question = question_dict.get(question_id)
                mark = get_question.mark
                correct_options = correct_answers.get(question_id, [])
                correct_answer = next(
                    (
                        opt.id
                        for opt in options_dict.get(question_id, [])
                        if opt.id in correct_options
                    ),
                    None,
                )                
                if option_id is not None:
                        try:
                            if int(option_id) == correct_answer:
                                rating = 1
                            else:
                                rating = 0
                        except ValueError:
                            rating = question_response.get("rating")
                else:
                        rating = 0
                feedback = {
                    "correctness": question_response.get("correctness"),
                    "rating": question_response.get("rating"),
                }

                response_list.append(
                    {
                        "id": question_id,
                        "response": option_id,
                        "correct_answer": correct_answer,
                        "feedback": feedback,
                        "rating": rating,
                        "mark": mark,
                    }
                )

        db.close()

        return {
            "answers": response_list,
            "question_paper_id": question_paper_id,
        }

    except Exception as e:
        db.close()
        raise HTTPException(status_code=500, detail=str(e))


@question_route.get("/get_essay_questions")
def get_essay_questions(
    paper_id: int,
    subject_id: int,
    user_data: dict = Depends(JWTBearer()),
    db: Session = Depends(get_db),
):
    """
    The function `get_essay_questions` retrieves questions with options and subquestions based on
    provided criteria from a database and organizes the data into a structured format.

    :param paper_id: The `paper_id` parameter in the `get_essay_questions` function represents
    the unique identifier of a question paper for which you want to retrieve questions with options.
    This parameter is used to filter the query results based on the specified question paper
    :type paper_id: int
    :param subject_id: The `subject_id` parameter in the `get_essay_questions` function is used
    to filter questions based on the subject to which they belong. This parameter helps in retrieving
    questions that are specifically related to a particular subject
    :type subject_id: int
    :param db: The function `get_essay_questions` retrieves questions with their options from a
    database based on the provided criteria. Here's a breakdown of the parameters used in the function:
    :type db: Session
    :return: The function `get_essay_questions` returns a list of dictionaries containing
    information about question papers, sections, questions, options, and subquestions based on the
    provided criteria such as `paper_id`, `subject_id`, and `introtext_id`. The data structure includes
    details like paper ID, paper name, year, section name, section title, question ID, question text,
    question type, options for
    """
    data = (
        db.query(QuestionPaper, Section, Question, Options)
        .join(Section, QuestionPaper.id == Section.question_paper_id)
        .join(Question, Section.id == Question.section_id)
        .outerjoin(Options, Question.id == Options.question_id)
        .filter(
            QuestionPaper.id == paper_id,
            Question.subject_id == subject_id,
            Question.deleted == DELETED,
            QuestionPaper.deleted == DELETED,
        )
        .all()
    )
    prompt = []
    unique_prompts = set()
    if not data:
        db.close()
        response = JSONResponse(
            content={
                "success": False,
                "message": "No questions found for the provided criteria",
                "status": status.HTTP_404_NOT_FOUND,
            }
        )
        response.status_code = status.HTTP_404_NOT_FOUND
        return response

    subquestions = (
        db.query(Question)
        .filter(Question.parent_id.isnot(None), Question.deleted == DELETED)
        .all()
    )

    subquestion_texts = {subquestion.id: subquestion for subquestion in subquestions}

    paper_sections = {}

    for paper, section, question, option in data:
        if paper.id not in paper_sections:
            paper_sections[paper.id] = {"paper_info": paper, "sections": {}}
        if section.id not in paper_sections[paper.id]["sections"]:
            paper_sections[paper.id]["sections"][section.id] = {
                "section_info": section,
                "questions": {},
            }
        if question.parent_id:
            if (
                question.parent_id
                not in paper_sections[paper.id]["sections"][section.id]["questions"]
            ):
                parent_question = (
                    db.query(Question).filter(Question.id == question.parent_id).first()
                )
                paper_sections[paper.id]["sections"][section.id]["questions"][
                    question.parent_id
                ] = {
                    "question_info": parent_question,
                    "options": [],
                    "sub_questions": [],
                    "question_text": (
                        parent_question.question_text if parent_question else ""
                    ),
                }
            parent_question_text = paper_sections[paper.id]["sections"][section.id][
                "questions"
            ][question.parent_id]["question_text"]
            paper_sections[paper.id]["sections"][section.id]["questions"][
                question.parent_id
            ]["sub_questions"].append(
                {
                    "question_id": question.id,
                    "question_text": question.question_text,
                    # "parent_question_id": question.parent_id,
                    # "parent_question_text": parent_question_text,
                    "score": question.mark if question.mark else None,
                    "source_text": (
                        question.source_text if question.source_text else None
                    ),
                    "question_number": (
                        question.question_number if question.question_number else None
                    ),
                    "question_type": (
                        question.question_type_id if question.question_type_id else None
                    ),
                    "options": [],
                }
            )
        elif question.question_type_id == ESSAY_QUESTION_TYPE_ID:
            paper_sections[paper.id]["sections"][section.id]["questions"][
                question.id
            ] = {
                "question_info": question,
                "options": [],
                "sub_questions": [],
                "question_text": question.question_text,
            }
        if question.prompt_text and question.id not in unique_prompts:
            prompt.append({"question_id": question.id, "value": question.prompt_text})
            unique_prompts.add(question.id)
    paper_sections_list = [
        {
            "paper_id": paper_id,
            "paper_name": paper_data["paper_info"].assessment_specification,
            "year": paper_data["paper_info"].year,
            "sections": [
                {
                    "name": section_data["section_info"].name,
                    "title": section_data["section_info"].description,
                    "questions": [
                        {
                            "question_id": question_id,
                            "question_text": question_data["question_text"],
                            "score": (
                                question_data["question_info"].mark
                                if question_data["question_info"]
                                else None
                            ),
                            "source_text": (
                                question_data["question_info"].source_text
                                if question_data["question_info"]
                                else None
                            ),
                            "question_number": (
                                question_data["question_info"].question_number
                                if question_data["question_info"]
                                else None
                            ),
                            "question_type": (
                                question_data["question_info"].question_type_id
                                if question_data["question_info"]
                                else None
                            ),
                            "options": question_data["options"],
                            "sub_questions": question_data["sub_questions"],
                        }
                        for question_id, question_data in section_data[
                            "questions"
                        ].items()
                    ],
                }
                for section_id, section_data in paper_data["sections"].items()
            ],
        }
        for paper_id, paper_data in paper_sections.items()
    ]

    db.close()
    return {"data": {"questions": paper_sections_list}, "prompt": prompt}
