from sqlalchemy import String, Enum
from sqlalchemy.orm import mapped_column
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from flask_bcrypt import generate_password_hash, check_password_hash

from app.models.basemodel import BaseModel
from app.models.base import Base
from app.utils.helpers import has_required_keys


class User(BaseModel):
    """
        User Model
        Attributes:
            first_name (str): The first name of the user. Must be a non-null string with a maximum length of 300 characters.
            last_name (str): The last name of the user. Must be a non-null string with a maximum length of 300 characters.
            email (str): The email address of the user. Must be a non-null string with a maximum length of 300 characters.
            password (str): The password of the user. Must be a non-null string stored as a hashed value.
            role (str): The role of the user. Must be one of 'admin' or 'student'. Defaults to 'student'.
        Methods:
            __init__(**kwargs): Initializes a User instance with the provided keyword arguments. Raises a ValueError if any required keys are missing.
            basic_info() -> dict: Returns a dictionary containing basic information about the user, including id, first_name, last_name, and email.
    """
    first_name = mapped_column(String(300), nullable=False)
    last_name = mapped_column(String(300), nullable=False)
    email = mapped_column(String(300), nullable=False)
    password = mapped_column(MEDIUMTEXT, nullable=False)
    role = mapped_column(Enum('admin', 'student',\
                              name='role', default='student'), default='student', nullable=False)

    def __init__(self, **kwargs):
        """
            Initialize a new User instance.
            Args:
                **kwargs: Arbitrary keyword arguments containing user attributes.
            Raises:
                ValueError: If any of the required keys ('first_name', 'last_name', 'email', 'password') are missing.
            Attributes:
                password (str): The hashed password of the user.
        """
        super().__init__()
        [setattr(self, key, value) for key, value in kwargs.items()]

        required_keys = {'first_name', 'last_name', 'email', 'password'}
        accurate, missing = has_required_keys(kwargs, required_keys)
        if not accurate:
            raise ValueError(f"Missing required keys: {', '.join(missing)}")

        self.password = generate_password_hash(self.password).decode()

    def update(self, **kwargs):
        if kwargs.get("password"):
            setattr(self, "password", generate_password_hash(kwargs["password"]))
            del kwargs["password"]
        super().update(**kwargs)

    def check_password(self, password: str) -> bool:
        """
        Check if the provided password matches the user's password.

        Args:
            password (str): The password to check against the user's password.

        Returns:
            bool: True if the passwords match, False otherwise.
        """
        return check_password_hash(self.password, password)

    def basic_info(self) -> dict:
        """
        Returns a dictionary containing the basic information of the user.

        Returns:
            dict: A dictionary with the user's id, first name, last name, and email.
        """
        info = {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
        }
        return info


class Admin(User, Base):
    """
    Admin class that inherits from User and Base.
    Attributes:
        __tablename__ (str): The name of the table in the database.
    Methods:
        __init__(**kwargs): Initializes an Admin instance with given keyword arguments.
    """
    __tablename__ = "admins"

    def __init__(self, **kwargs):
        """
        Initialize a new User instance with the given keyword arguments.

        Args:
            **kwargs: Arbitrary keyword arguments passed to the superclass initializer.
        """
        super().__init__(**kwargs)

class Student(User, Base):
    """
    Represents a student in the system.
    Attributes:
        __tablename__ (str): The name of the table in the database.
    Methods:
        __init__(**kwargs): Initializes a new instance of the Student class.
    """
    __tablename__ = "students"

    def __init__(self, **kwargs):
        """
        Initialize a new instance of the class.

        Parameters:
        **kwargs: Arbitrary keyword arguments passed to the superclass initializer.
        """
        super().__init__(**kwargs)