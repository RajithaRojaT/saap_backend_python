from fastapi import FastAPI, staticfiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from app.login.auth import JWTBearer
from database import Base, engine
from app.questions.questionPaperApi import questionpaperroute
from app.questions.OptionsApi import optionsroute
from app.login.api import auth_route
from app.subject.subjectApi import subjectroute
from app.subject.sectionApi import sectionapiroute
from app.questions.introtextApi import introtextroute
from app.questions.question import question_route

from app.payment.paymentApi import payments
from app.dashboard.teacherDashboard import studentsroute
from app.ai.api import *
from app.rolemanagement.api import rolemanager


app = FastAPI()
# The line `app.mount("/uploads", staticfiles.StaticFiles(directory="uploads"))` is mounting a
# directory named "uploads" to the "/uploads" path in the FastAPI application. This allows the FastAPI
# application to serve static files from the specified directory. In this case, any files stored in
# the "uploads" directory will be accessible via the "/uploads" URL path in the application.

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
# The line `app.mount("/uploads", staticfiles.StaticFiles(directory="uploads"))` is mounting a
# directory named "uploads" to the "/uploads" path in the FastAPI application. This allows the FastAPI
# application to serve static files from the specified directory. In this case, any files stored in
# the "uploads" directory will be accessible via the "/uploads" URL path in the application. This is
# useful for serving static files such as images, CSS files, JavaScript files, etc., from the
# specified directory in the FastAPI application.


origins = ["*"]
# app.add_middleware(
    # CORSMiddleware,
    # allow_origins=origins,
    # allow_credentials=True,
    # allow_methods=["*"],
    # allow_headers=["*"],
# )

Base.metadata.create_all(bind=engine)
app.mount("/uploads", staticfiles.StaticFiles(directory="uploads"))
app.mount("/invoices", staticfiles.StaticFiles(directory="invoices"))
app.include_router(optionsroute)
app.include_router(introtextroute)
app.include_router(auth_route)
app.include_router(subjectroute)
app.include_router(questionpaperroute)
app.include_router(sectionapiroute)
app.include_router(payments)
app.include_router(studentsroute)
app.include_router(question_route)
app.include_router(ai_route)
app.include_router(rolemanager)
