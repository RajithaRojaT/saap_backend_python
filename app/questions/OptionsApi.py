import shutil
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.login.auth import JWTBearer
from app.models import Options, Question
from starlette import status
from app.params import DELETED
from app.questions.basemodel import CreateOptions
from database import get_db
import os

 
optionsroute = APIRouter(prefix= '/options', tags= ['options'])
 
@optionsroute.get("/")
def get_options_by_questions(question_paper_id:int,db: Session = Depends(get_db), user_data: dict = Depends(JWTBearer())):
        question_paper = db.query(Options).filter(Options.question_id == question_paper_id, Options.deleted == DELETED).all()
        db.close()
        if not question_paper:
            response = JSONResponse(content={"success": False, "message": "Question Paper not found", "status": status.HTTP_404_NOT_FOUND})
            response.status_code = status.HTTP_404_NOT_FOUND
            return response
        return question_paper
 
@optionsroute.post("/create")
def create_options(create_option: CreateOptions, db: Session = Depends(get_db), user_data: dict = Depends(JWTBearer())):
    try:
        question = db.query(Question).filter(Question.id == create_option.question_id, Question.deleted == DELETED).first()
        if not question:
            response = JSONResponse(content={"success": False, "message": "Question not found", "status": status.HTTP_404_NOT_FOUND})
            response.status_code = status.HTTP_404_NOT_FOUND
            return response
        add_option = Options(
            text=create_option.text,
            option_label=create_option.option_label,
            is_correct=create_option.is_correct,
            score=create_option.score,
            feedback=create_option.feedback,
            question_id=create_option.question_id,
            created_by_id=1
        )
        db.add(add_option)
        db.commit()
        db.close()
        return {"Message": "Options Created Successfully"}
    except Exception as e:
        db.rollback()
        db.close()
        return {"Error": str(e)}
   
 
@optionsroute.put("/update")
def update_options(option_id:int, update_option: CreateOptions, db: Session = Depends(get_db), user_data: dict = Depends(JWTBearer())):
    try:
        question = db.query(Question).filter(Question.id == update_option.question_id, Question.deleted == DELETED).first()
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        option = db.query(Options).filter(Options.id == option_id, Options.deleted == DELETED).first()
        if not option:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Option not found")
        option.text = update_option.text
        option.option_label = update_option.option_label
        option.is_correct = update_option.is_correct
        option.score = update_option.score
        option.feedback = update_option.feedback
        option.question_id = update_option.question_id
        db.commit()
        db.close()
        return {"Message": "Options Updated Successfully"}
    except Exception as e:
        db.rollback()
        db.close()
        
        return {"Error":str(e)}
