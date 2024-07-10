import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.login.auth import JWTBearer
from app.models import PaperScore, QuestionPaper, Subject, User, UserResponse
from app.params import DELETED
from database import get_db

studentsroute = APIRouter(prefix="/students", tags=["students"])


@studentsroute.get("/list")
def get_students(
    db: Session = Depends(get_db),
    user_data: dict = Depends(JWTBearer()),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, le=100),
):
    """
    Retrieve all students data from the database with pagination.
    """
    students = (
        db.query(User)
        .filter(User.deleted == DELETED,User.role_id ==1)
        .limit(per_page)
        .offset((page - 1) * per_page)
        .all()
    )
    return students


@studentsroute.get("/student_dashbord")
def get_user_response_details(
    user_id: int, db: Session = Depends(get_db), user_data: dict = Depends(JWTBearer())
):
    """
    This function retrieves user response details along with related subject and question paper
    information based on the user ID.

    :param user_id: The `user_id` parameter is used to identify the specific user for whom we want to
    retrieve response details. This parameter is of type integer and is passed to the
    `get_user_response_details` function to fetch the user's responses from the database
    :type user_id: int
    :param db: The `db` parameter in the function `get_user_response_details` is an instance of the
    database session. It is used to interact with the database to query and retrieve information related
    to user responses, subjects, and question papers. The `db` parameter is injected into the function
    using `Depends
    :type db: Session
    :return: The function `get_user_response_details` returns a list of dictionaries containing details
    of user responses along with related subject and question paper information. Each dictionary in the
    list includes the following keys:
    - "question_paper_id": ID of the question paper
    - "subject_id": ID of the subject
    - "total_score": Total score of the user response
    - "year": Year of the response
    """
    try:
        # user_responses = db.query(UserResponse).filter(UserResponse.user_id == user_id).all()
        # if not user_responses:
        #     raise HTTPException(status_code=404, detail="User responses not found")

        user_responses_with_related = (
            db.query(UserResponse, Subject, QuestionPaper)
            .join(Subject, UserResponse.subject_id == Subject.id, isouter=True)
            .join(
                QuestionPaper,
                UserResponse.question_paper_id == QuestionPaper.id,
                isouter=True,
            )
            .filter(UserResponse.user_id == user_id)
            .all()
        )

        response_details = []
        for response, subject, question_paper in user_responses_with_related:
            user_response_data = json.loads(response.user_response)
            response_detail = {
                "question_paper_id": response.question_paper_id,
                "subject_id": response.subject_id,
                "total_score": response.total_score,
                "time": user_response_data.get("time"),
                "year": response.year,
                "exam_date": response.created_at,
                "subject_name": subject.subject_name if subject else None,
                "topic_name": question_paper.topic_name if question_paper else None,
                "assessment_specification": (
                    question_paper.assessment_specification if question_paper else None
                ),
                "result_id": response.id,
            }
            response_details.append(response_detail)

        return response_details
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
