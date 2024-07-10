import select
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from requests import Session
from sqlalchemy.orm import Session
from sqlalchemy import select, join
from app.login.auth import JWTBearer
from app.models import Role, User
from database import get_db
from pydantic import BaseModel


class UserRoleUpdate(BaseModel):
    user_id: int
    new_role_id: int


rolemanager = APIRouter(prefix="/role")


"""
    The function `listuser` retrieves user data including name, email, id, role_id, and role name by
    joining the User and Role tables.
    
    :param db: The `db` parameter is used to access the database session within the `listuser` function.
    It is of type `Session` which is typically a database session object used for querying the database
    :type db: Session
    :param user_data: The `user_data` parameter in the `listuser` function is used to extract the user
    data from the JWT token passed in the request. This parameter is decorated with
    `Depends(JWTBearer())`, which indicates that the function depends on the JWT token for
    authentication and authorization purposes. The user
    :type user_data: dict
    :return: The code snippet is defining a FastAPI endpoint at the route "/list_user" that requires a
    database session and user data obtained from a JWT token. The endpoint executes a SQL query to
    retrieve data about users and their roles from the database. The query selects the user's name,
    email, id, role_id, and the corresponding role name by joining the User and Role tables on the
    role_id.
"""


@rolemanager.get("/list_user")
def listuser(db: Session = Depends(get_db), user_data: dict = Depends(JWTBearer())):
    stmt = select(
        User.name, User.email, User.id, User.role_id, Role.name.label("role_name")
    ).select_from(join(User, Role, User.role_id == Role.id))
    result = db.execute(stmt).all()

    return {"data": result}


@rolemanager.get("/rolelist")
def listrole(db: Session = Depends(get_db), user_data: dict = Depends(JWTBearer())):
    """
    The function `listrole` retrieves a list of role IDs and names from the database.

    :param db: The `db` parameter is of type `Session` and is obtained by calling the `get_db` function
    using the `Depends` function. This parameter is used to interact with the database within the
    `listrole` function
    :type db: Session
    :param user_data: The user_data parameter is a dictionary containing data extracted from the JWT
    (JSON Web Token) provided in the request header. This data typically includes information about the
    authenticated user, such as their user ID, username, and any additional claims or roles associated
    with the user. In this case, the JWTBearer
    :type user_data: dict
    :return: A dictionary with the key "data" containing a list of tuples with the id and name of roles
    from the database.
    """
    rolelist = db.query(Role.id, Role.name).all()
    return {"data": rolelist}


@rolemanager.put("/update_user_role")
def update_user_roles(request: List[UserRoleUpdate],db: Session = Depends(get_db),user_data: dict = Depends(JWTBearer())):
    """
    This function updates user roles based on the provided UserRoleUpdate requests and returns a
    response with updated user roles and any errors encountered.
    
    :param request: The `request` parameter in the `update_user_roles` function is expected to be a list
    of `UserRoleUpdate` objects. Each `UserRoleUpdate` object should contain information about the user
    ID (`user_id`) and the new role ID (`new_role_id`) that you want to update for that
    :type request: List[UserRoleUpdate]
    :param db: The `db` parameter in the function `update_user_roles` is a dependency that provides a
    database session. It is used to interact with the database to query and update user and role
    information based on the input provided in the `request` parameter. The `db` parameter is passed as
    a keyword
    :type db: Session
    :param user_data: The `user_data` parameter in the `update_user_roles` function seems to be used for
    JWT (JSON Web Token) authentication. It is likely being used to authenticate and authorize the user
    making the request. The `JWTBearer` dependency is probably responsible for validating the JWT token
    provided in the request
    :type user_data: dict
    :return: The function `update_user_roles` returns a dictionary with keys "data" containing another
    dictionary with keys "updated" and "errors". The "updated" key contains a list of dictionaries with
    "user_id" and "new_role_id" keys for successfully updated user roles. The "errors" key contains a
    list of dictionaries with "user_id" and "error" keys for any errors encountered during
    """
    response = {"updated": [], "errors": []}

    for update in request:
        user = db.query(User).filter(User.id == update.user_id).first()
        if not user:
            response["errors"].append(
                {"user_id": update.user_id, "error": "User not found"}
            )
            continue

        role = db.query(Role).filter(Role.id == update.new_role_id).first()
        if not role:
            response["errors"].append(
                {"user_id": update.user_id, "error": "Role not found"}
            )
            continue

        user.role_id = update.new_role_id
        db.commit()
        response["updated"].append(
            {"user_id": update.user_id, "new_role_id": update.new_role_id}
        )

    return {"data": response}
