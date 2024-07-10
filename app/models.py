from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    Float,
    String,
    Text,
    Boolean,
    text,
    Enum,
    Date,
    TIMESTAMP,
)
from sqlalchemy.sql import func
from database import Base
from sqlalchemy.dialects.mysql import JSON


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    email = Column(String(100), unique=True, nullable=False)
    picture_url = Column(String(255))
    authentication_type = Column(String(255), nullable=False)
    external_login_id = Column(String(255), unique=True)
    role_id = Column(Integer, default="1", nullable=False)
    stripe_id = Column(String(100))
    created_at = Column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at = Column(
        DateTime, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
    )
    created_by = Column(Integer, ForeignKey("user.id"))
    updated_by = Column(Integer, ForeignKey("user.id"))
    deleted = Column(SmallInteger, default="0")
    record_status = Column(SmallInteger, default="1")


class Subject(Base):
    __tablename__ = "subject"

    id = Column(
        Integer, primary_key=True, index=True, nullable=False, autoincrement=True
    )
    subject_name = Column(String(255), nullable=False)
    subject_code = Column(String(255), nullable=False)
    created_at = Column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at = Column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    deleted = Column(SmallInteger, nullable=False, server_default=text("0"))
    record_status = Column(SmallInteger, nullable=False, server_default=text("1"))
    created_by_id = Column(Integer, nullable=False)
    updated_by_id = Column(Integer)


class QuestionPaper(Base):
    __tablename__ = "question_paper"

    id = Column(
        Integer, primary_key=True, index=True, nullable=False, autoincrement=True
    )
    assessment_specification = Column(String(255), nullable=False)
    topic_name = Column(Text, nullable=False)
    year = Column(Integer, nullable=False)
    subject_id = Column(Integer, ForeignKey("subject.id"), nullable=False)
    created_at = Column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at = Column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    deleted = Column(SmallInteger, nullable=False, server_default=text("0"))
    record_status = Column(SmallInteger, nullable=False, server_default=text("1"))
    created_by_id = Column(Integer, nullable=False)
    updated_by_id = Column(Integer)


class Section(Base):
    __tablename__ = "section"

    id = Column(
        Integer, primary_key=True, index=True, nullable=False, autoincrement=True
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    question_paper_id = Column(Integer, ForeignKey("question_paper.id"), nullable=False)
    created_at = Column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at = Column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    deleted = Column(SmallInteger, nullable=False, server_default=text("0"))
    record_status = Column(SmallInteger, nullable=False, server_default=text("1"))
    created_by_id = Column(Integer, nullable=False)
    updated_by_id = Column(Integer)


class IntroText(Base):
    __tablename__ = "introtext"

    id = Column(
        Integer, primary_key=True, index=True, nullable=False, autoincrement=True
    )
    name = Column(String(255), nullable=False)
    type = Column(Enum("Text", "image"), nullable=False)
    created_at = Column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at = Column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    deleted = Column(SmallInteger, nullable=False, server_default=text("0"))
    record_status = Column(SmallInteger, nullable=False, server_default=text("1"))
    created_by_id = Column(Integer, nullable=False)
    updated_by_id = Column(Integer)


class Question(Base):
    __tablename__ = "question"

    id = Column(
        Integer, primary_key=True, index=True, nullable=False, autoincrement=True
    )
    parent_id = Column(Integer, ForeignKey("question.id"), nullable=True)
    paper_id = Column(Integer, ForeignKey("question_paper.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    question_type_id = Column(Integer, ForeignKey("question_paper.id"), nullable=False)
    question_rule = Column(Text, nullable=True)
    question_number = Column(Integer, nullable=False)
    subquestion_label = Column(String(255), nullable=False)
    order = Column(Integer, nullable=True)
    subject_id = Column(Integer, ForeignKey("subject.id"), nullable=False)
    section_id = Column(Integer, ForeignKey("section.id"), nullable=False)
    introtext = Column(Text, nullable=True)
    mark = Column(Float, nullable=False)
    source_text = Column(String(255), nullable=False)
    created_at = Column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at = Column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    deleted = Column(SmallInteger, nullable=False, server_default=text("0"))
    record_status = Column(SmallInteger, nullable=False, server_default=text("1"))
    created_by_id = Column(Integer, nullable=False)
    updated_by_id = Column(Integer)
    prompt_text = Column(Text, nullable=True)


class PaperScore(Base):
    __tablename__ = "paper_score"

    id = Column(
        Integer, primary_key=True, index=True, nullable=False, autoincrement=True
    )
    paper_id = Column(Integer, ForeignKey("question_paper.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    score = Column(Integer, nullable=True)
    created_at = Column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at = Column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    deleted = Column(SmallInteger, nullable=False, server_default=text("0"))
    record_status = Column(SmallInteger, nullable=False, server_default=text("1"))
    created_by_id = Column(Integer, nullable=False)


class Role(Base):
    __tablename__ = "roles"

    id = Column(
        Integer, primary_key=True, index=True, nullable=False, autoincrement=True
    )
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at = Column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    deleted = Column(SmallInteger, nullable=False, server_default=text("0"))
    record_status = Column(SmallInteger, nullable=False, server_default=text("1"))
    created_by_id = Column(Integer, nullable=False)
    updated_by_id = Column(Integer)


class UserRole(Base):
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    subscriber_id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False, default=1)
    created_at = Column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at = Column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    deleted = Column(SmallInteger, nullable=False, server_default=text("0"))
    record_status = Column(SmallInteger, nullable=False, server_default=text("1"))
    created_by_id = Column(Integer, nullable=False)
    updated_by_id = Column(Integer)


class Options(Base):
    __tablename__ = "option"

    id = Column(
        Integer, primary_key=True, index=True, nullable=False, autoincrement=True
    )
    text = Column(String(255), nullable=True)
    option_label = Column(String(255), nullable=True)
    is_correct = Column(Boolean, nullable=False)
    score = Column(Float, nullable=False)
    feedback = Column(String(255), nullable=True)
    question_id = Column(Integer, ForeignKey("question.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now())
    deleted = Column(SmallInteger, nullable=False, default=0)
    record_status = Column(SmallInteger, nullable=False, default=1)
    created_by_id = Column(Integer, nullable=False)
    updated_by_id = Column(Integer)


class Endpoint(Base):
    __tablename__ = "endpoint"
    id = Column(
        Integer, primary_key=True, index=True, nullable=False, autoincrement=True
    )
    url = Column(String(255), nullable=True)
    default_role_access_id = Column(Integer, ForeignKey("roles.id"), default=1)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now())
    deleted = Column(SmallInteger, nullable=False, default=0)
    record_status = Column(SmallInteger, nullable=False, default=1)
    created_by_id = Column(Integer, nullable=False)
    updated_by_id = Column(Integer)


class PaymentHistory(Base):
    __tablename__ = "payment_history"

    id = Column(
        Integer, primary_key=True, autoincrement=True, unique=True, nullable=False
    )
    payment_date = Column(Date, nullable=False)
    total_amount = Column(Integer, nullable=False)
    status = Column(String(length=255), nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, server_default="CURRENT_TIMESTAMP")
    updated_at = Column(TIMESTAMP, server_default="CURRENT_TIMESTAMP")
    deleted = Column(SmallInteger, nullable=False, server_default="0")
    record_status = Column(SmallInteger, nullable=False, server_default="1")
    created_by_id = Column(Integer, nullable=False)
    updated_by_id = Column(Integer, nullable=True)
    stripe_payment_intent_id = Column(String(length=255), nullable=True)
    stripe_checkout_id = Column(String(length=255), nullable=False)
    customer_id = Column(String(length=255), nullable=True)
    stripe_transaction_status = Column(String(length=255), nullable=False)
    cancelled_date = Column(Date, nullable=True)
    cancellation_type = Column(Integer, nullable=True)
    next_payment_date = Column(Date, nullable=True)
    payment_intent_detail = Column(JSON)
    checkout_detail = Column(JSON)
    invoice_detail = Column(JSON)


class Invoice(Base):
    __tablename__ = "invoice"

    id = Column(Integer, primary_key=True, autoincrement=True, unique=True)
    payment_id = Column(Integer, nullable=False, index=True)
    payment_date = Column(Date, nullable=False)
    status = Column(String(length=255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now())
    deleted = Column(SmallInteger, nullable=False, default=0)
    record_status = Column(SmallInteger, nullable=False, default=1)
    created_by_id = Column(Integer, nullable=False)
    updated_by_id = Column(Integer, nullable=True)
    stripe_invoice_id = Column(String(length=255), nullable=False)
    invoice_detail = Column(JSON)
    next_invoice_date = Column(Date, nullable=True)
    invoice_status = Column(String(length=255), nullable=True)
    file_path = Column(String(length=500), nullable=True)


class UserResponse(Base):
    __tablename__ = "user_response"

    id = Column(
        Integer, primary_key=True, index=True, nullable=False, autoincrement=True
    )
    user_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    question_paper_id = Column(Integer, ForeignKey("question_paper.id"), nullable=True)
    subject_id = Column(Integer, ForeignKey("subject.id"), nullable=True)
    year = Column(Integer)
    user_response = Column(JSON, nullable=False)
    total_score = Column(Float, nullable=True)
    created_at = Column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at = Column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    deleted = Column(SmallInteger, nullable=False, server_default=text("0"))
    record_status = Column(SmallInteger, nullable=False, server_default=text("1"))
    created_by_id = Column(Integer, nullable=False)
    updated_by_id = Column(Integer)
    ai_response = Column(JSON)


class QuestionType(Base):
    __tablename__ = "question_type"

    id = Column(
        Integer, primary_key=True, index=True, nullable=False, autoincrement=True
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at = Column(
        DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    deleted = Column(SmallInteger, nullable=False, server_default=text("0"))
    record_status = Column(SmallInteger, nullable=False, server_default=text("1"))
    created_by_id = Column(Integer, nullable=False)
    updated_by_id = Column(Integer)


class LogoutToken(Base):
    __tablename__ = 'logout_token'
    
    id = Column(Integer, primary_key=True, autoincrement=True, unique=True, nullable=False)
    user_id = Column(Integer, nullable=False)
    token = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    deleted = Column(SmallInteger, nullable=False, server_default="0")
    record_status = Column(SmallInteger, nullable=False, server_default="1")
    created_by_id = Column(Integer, nullable=False)
    updated_by_id = Column(Integer, nullable=True)