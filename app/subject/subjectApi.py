from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.login.auth import JWTBearer
from app.models import Subject
from app.params import DELETED
from app.subject.basemodel import SubjectCreate
from database import get_db
from starlette import status

subjectroute = APIRouter(prefix="/subject", tags=["subject"])
subjectpaperroute = APIRouter(prefix="/subjectpaperroute", tags=["subject paper"])


@subjectroute.get("/get")
def get_subject(db: Session = Depends(get_db), user_data: dict = Depends(JWTBearer())):
    subjects = db.query(Subject).filter(Subject.deleted == DELETED).all()
    db.close()
    return subjects


@subjectroute.post("")
async def create_subject(
    subject_request: SubjectCreate,
    db: Session = Depends(get_db),
    user_data: dict = Depends(JWTBearer()),
):
    try:
        subject = Subject(
            subject_name=subject_request.subject_name,
            subject_code=subject_request.subject_code,
            created_by_id=1,
        )
        db.add(subject)
        db.commit()
        db.close()
        return {"Message": "Subject Created Successfully"}
    except Exception as e:
        db.rollback()
        db.close()
        return {"error": str(e)}


@subjectroute.put("/update")
async def update_subject(
    subject_id: int,
    subject_update_request: SubjectCreate,
    db: Session = Depends(get_db),
    user_data: dict = Depends(JWTBearer())
):
    try:
        subject = (
            db.query(Subject)
            .filter(Subject.id == subject_id, Subject.deleted == DELETED)
            .first()
        )
        if not subject:
            db.close()
            response = JSONResponse(content={"success": False, "message": "Question Paper not found", "status": status.HTTP_404_NOT_FOUND})
            response.status_code = status.HTTP_404_NOT_FOUND
            return response
        if subject.deleted:
            db.close()
            raise HTTPException(status_code=404, detail="Subject is deleted")

        subject.subject_name = subject_update_request.subject_name
        subject.subject_code = subject_update_request.subject_code
        subject.updated_by_id = 2

        db.commit()
        db.close()
        return {"Message": "Subject Updated Successfully"}
    except Exception as e:
        db.rollback()
        db.close()
        return {"error": str(e)}


@subjectroute.delete("/")
async def delete_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    user_data: dict = Depends(JWTBearer())
):
    try:
        subject = db.query(Subject).filter(Subject.id == subject_id).first()
        if not subject:
            db.close()
            response = JSONResponse(content={"success": False, "message": "Subject not found", "status": status.HTTP_404_NOT_FOUND})
            response.status_code = status.HTTP_404_NOT_FOUND
            return response
        if subject.deleted:
            db.close()
            raise HTTPException(status_code=400, detail="Subject is already deleted")

        subject.deleted = True

        db.commit()
        db.close()
        return {"Message": "Subject Deleted Successfully"}
    except Exception as e:
        db.rollback()
        db.close()
        return {"error": str(e)}
