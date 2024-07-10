import os
from fastapi import FastAPI
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv
from app.models import Role, User
from database import Base, get_db


# Load environment variables from .env file
load_dotenv()

# Read database URL from environment variable
DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "mysql+pymysql://root:@localhost:3306/saap"
)

# Create an engine and session for the test database
engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Override the get_db dependency to use the test database
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app = FastAPI()
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


# Fixture to set up the database with some initial data
@pytest.fixture(scope="module")
def setup_db():
    try:
        Base.metadata.create_all(bind=engine)
        db = TestingSessionLocal()

        # Create the roles "student" and "staff"
        admin_user = User(name="Admin User", email="admin@example.com")
        db.add(admin_user)
        db.commit()
        role_student = Role(
            name="student", created_by_id=admin_user.id, updated_by_id=admin_user.id
        )
        role_staff = Role(
            name="staff", created_by_id=admin_user.id, updated_by_id=admin_user.id
        )
        db.add(role_student)
        db.add(role_staff)
        db.commit()
        # Create some initial users
        user1 = User(
            name="User1",
            email="user1@example.com",
            role_id=role_student.id,
            created_by_id=admin_user.id,
            updated_by_id=admin_user.id,
            authentication_type="test"
        )
        user2 = User(
            name="User2",
            email="user2@example.com",
            role_id=role_staff.id,
            created_by_id=admin_user.id,
            updated_by_id=admin_user.id,
            authentication_type="test"
        )
        db.add(user1)
        db.add(user2)
        db.commit()
    except OperationalError as e:
        print(f"Operational error: {e}")
    finally:
        db.close()

    yield

    Base.metadata.drop_all(bind=engine)


def test_list_users(setup_db):
    response = client.get("/list_user")
    assert response.status_code == 200
    users = response.json()
    assert len(users) == 2
    assert users[0]["name"] == "User1"
    assert users[1]["name"] == "User2"


def test_update_user_roles(setup_db):
    payload = [{"user_id": 1, "new_role_id": 2}, {"user_id": 2, "new_role_id": 1}]
    response = client.put("/update_user_roles", json=payload)
    assert response.status_code == 200
    result = response.json()
    assert len(result["updated"]) == 2
    assert result["updated"][0]["user_id"] == 1
    assert result["updated"][0]["new_role_id"] == 2
    assert result["updated"][1]["user_id"] == 2
    assert result["updated"][1]["new_role_id"] == 1
