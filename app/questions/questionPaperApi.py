from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette import status
from app.login.auth import JWTBearer
from app.models import *
from app.params import DELETED
from app.questions.basemodel import CreateQuestionPaper
from database import get_db

questionpaperroute = APIRouter(prefix="/question-paper", tags=["Question Paper"])

@questionpaperroute.get("/alldata")
def get_question_papers(
   db: Session = Depends(get_db),
   user_data: dict = Depends(JWTBearer()),
   ):
   """
    This function retrieves all question papers from the database.
    :param db: The `db` parameter in the `get_question_papers` function is of type `Session`, which is
    likely referring to a database session object. This parameter is being injected using
    `Depends(get_db)`, which suggests that `get_db` is a dependency function that provides the database
    session to
    :type db: Session
    :return: A list of all question papers stored in the database.
    """
   papers = db.query(QuestionPaper).filter(QuestionPaper.deleted == DELETED).all()
   db.close()
   return papers

@questionpaperroute.get("/listyear")
def get_question_papers(
    db: Session = Depends(get_db),
    user_data: dict = Depends(JWTBearer()),
    ):
    """
    The function `get_question_papers` retrieves a list of unique years from the QuestionPaper table in
    the database.
    
    :param db: The `db` parameter in the `get_question_papers` function is of type `Session`, which is
    being injected into the function using `Depends(get_db)`. This parameter represents a database
    session that will be used to interact with the database when querying for question paper years
    :type db: Session
    :return: A list of all the years for which question papers are available in the database.
    """
    paper_year = db.query(QuestionPaper.year).all()
    db.close()
    return paper_year


@questionpaperroute.get("")
def get_question_papers(
    subject_id: int,
    db: Session = Depends(get_db),
    user_data: dict = Depends(JWTBearer()),
):
    """
    This function retrieves question papers for a specific subject from the database.
    
    :param subject_id: The `subject_id` parameter is an integer that represents the ID of the subject
    for which you want to retrieve question papers. This parameter is used to filter the question papers
    based on the subject ID in the database query
    :type subject_id: int
    :param db: The `db` parameter in the `get_question_papers` function is a dependency that provides a
    database session. It is used to interact with the database to query and retrieve question papers
    based on the provided `subject_id`. The `db` parameter is of type `Session` which is likely an
    :type db: Session
    :return: A list of question papers that belong to the specified subject ID and have not been marked
    as deleted.
    """
    question_papers = db.query(QuestionPaper).filter(
        QuestionPaper.subject_id == subject_id,
        QuestionPaper.deleted == DELETED
    ).all()
    db.close()
    return question_papers

@questionpaperroute.get("/year")
def get_question_papers(
    year: int,
    db: Session = Depends(get_db),
    user_data: dict = Depends(JWTBearer()),
):
    """
    This function retrieves question papers from the database based on the specified year.
    
    :param year: The `year` parameter in the code snippet represents the year for which you want to
    retrieve question papers. It is expected to be an integer value that specifies the year of the
    question papers you are looking for
    :type year: int
    :param db: The `db` parameter in the code snippet is a dependency that is used to interact with the
    database. It is of type `Session`, which is likely an instance of a database session that allows you
    to query the database and perform operations like adding, updating, or deleting records
    :type db: Session
    :return: A list of question papers from the database that match the specified year and have not been
    marked as deleted.
    """
    question_papers = db.query(QuestionPaper).filter(
        QuestionPaper.year == year,
        QuestionPaper.deleted == DELETED
    ).all()
    db.close()
    return question_papers

@questionpaperroute.get("/sub_year")
def get_question_papers(
    year: int,
    subject_id: int,
    db: Session = Depends(get_db),
    user_data: dict = Depends(JWTBearer())
):
    """
    This function retrieves question papers based on the specified year and subject ID from the
    database.
    
    :param year: The `year` parameter in the `get_question_papers` function represents the year for
    which you want to retrieve question papers. It is expected to be an integer value that specifies the
    year of the question papers you are looking for
    :type year: int
    :param subject_id: The `subject_id` parameter in the code snippet represents the unique identifier
    for a subject in the database. It is used to filter question papers based on the specified subject
    :type subject_id: int
    :param db: The `db` parameter in the `get_question_papers` function is a dependency parameter that
    represents the database session. It is used to interact with the database to query and retrieve
    question papers based on the provided `year` and `subject_id`. The `db` parameter is of type
    `Session
    :type db: Session
    :return: A list of question papers that match the specified year and subject ID, and have not been
    deleted.
    """
    question_papers = db.query(QuestionPaper).filter(
        QuestionPaper.year == year,QuestionPaper.subject_id==subject_id,
        QuestionPaper.deleted == DELETED
    ).all()
    db.close()
    return question_papers


@questionpaperroute.get("/question_paper_id")
def get_question_paper(
    question_paper_id: int,
    db: Session = Depends(get_db),
    user_data: dict = Depends(JWTBearer())
):
    """
    This function retrieves a question paper from the database based on the provided question paper ID.
    
    :param question_paper_id: The `question_paper_id` parameter is the unique identifier for a specific
    question paper. This endpoint is designed to retrieve a question paper from the database based on
    this identifier
    :type question_paper_id: int
    :param db: The `db` parameter in the `get_question_paper` function is used to access the database
    session. It is of type `Session` and is obtained using the `get_db` function as a dependency. This
    parameter allows the function to interact with the database to retrieve the question paper with the
    specified
    :type db: Session
    :return: The `get_question_paper` function returns a question paper object based on the provided
    `question_paper_id`. If the question paper with the specified ID is not found in the database or if
    it has been marked as deleted, a 404 Not Found HTTP exception is raised with the message "Question
    Paper not found".
    """
    question_paper = db.query(QuestionPaper).filter(QuestionPaper.id == question_paper_id, QuestionPaper.deleted == DELETED ).first()
    if not question_paper:
        db.close()
        response = JSONResponse(content={"success": False, "message": "Question Paper not found", "status": status.HTTP_404_NOT_FOUND})
        response.status_code = status.HTTP_404_NOT_FOUND
        return response
    db.close()
    return question_paper


@questionpaperroute.post("/create")
async def create_question_paper(
    create_paper: CreateQuestionPaper,
    db: Session = Depends(get_db),
    user_data: dict = Depends(JWTBearer())
):
    try:
        subject = db.query(Subject).filter(Subject.id == create_paper.subject_id, Subject.deleted == DELETED).first()
        if not subject:
            db.close()
            response = JSONResponse(content={"success": False, "message": "subject not found", "status": status.HTTP_404_NOT_FOUND})
            response.status_code = status.HTTP_404_NOT_FOUND
            return response
        question_paper = QuestionPaper(
            title=create_paper.title,
            description=create_paper.description,
            year=create_paper.year,
            month=create_paper.month,
            subject_id=create_paper.subject_id,
            created_by_id=1
        )

        db.add(question_paper)
        db.commit()
        db.close()
        return {"Message": "Question Paper Created Successfully"}
    except Exception as e:
        db.rollback()
        db.close()
        return {"error": str(e)}


@questionpaperroute.put("/update")
async def update_question_paper(
    question_paper_id: int,
    question_paper_update: CreateQuestionPaper,
    db: Session = Depends(get_db),
     user_data: dict = Depends(JWTBearer())
):
    try:
        question_paper = db.query(QuestionPaper).filter(QuestionPaper.id == question_paper_id, QuestionPaper.deleted == DELETED ).first()
        if not question_paper:
            db.close()
            response = JSONResponse(content={"success": False, "message": "Question Paper not found", "status": status.HTTP_404_NOT_FOUND})
            response.status_code = status.HTTP_404_NOT_FOUND
            return response        
        subject = db.query(Subject).filter(Subject.id == question_paper_update.subject_id, Subject.deleted == DELETED).first()
        if not subject:
            db.close()
            response = JSONResponse(content={"success": False, "message": "Subject not found", "status": status.HTTP_404_NOT_FOUND})
            response.status_code = status.HTTP_404_NOT_FOUND
            return response        
        question_paper.title = question_paper_update.title
        question_paper.description = question_paper_update.description
        question_paper.year = question_paper_update.year
        question_paper.month = question_paper_update.month
        question_paper.subject_id = question_paper_update.subject_id
        
        db.commit()
        db.close()
        return {"Message": "Question Paper Updated Successfully"}
    except Exception as e:
        db.rollback()
        db.close()
        return {"error": str(e)}


@questionpaperroute.delete("/")
async def delete_question_paper(
    question_paper_id: int,
    db: Session = Depends(get_db),
    user_data: dict = Depends(JWTBearer())
):
    try:
        question_paper = db.query(QuestionPaper).filter(QuestionPaper.id == question_paper_id, QuestionPaper.deleted == DELETED ).first()
        if not question_paper:
            db.close()
            response = JSONResponse(content={"success": False, "message": "Question Paper not found", "status": status.HTTP_404_NOT_FOUND})
            response.status_code = status.HTTP_404_NOT_FOUND
            return response
        question_paper.deleted = True
        db.commit()
        db.close()
        return {"Message": "Question Paper Deleted Successfully"}
    except Exception as e:
        db.rollback()
        db.close()
        return {"error": str(e)}

