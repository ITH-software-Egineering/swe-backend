from datetime import datetime, timezone
from typing import Optional, List
from uuid import uuid4
import copy

from sqlalchemy import String, DateTime
from sqlalchemy.orm import mapped_column
from flask import g


class BaseModel:
    """
    Class:
        BaseModel: The base class most models will inherit from.
            It contains most of the methods needed by each database models

        :methods
            delete: Deletes an object from the current session
            add: adds an object to the current database session
            save: persist the object details in the database
    """
    
    id = mapped_column(String(60), default=str(uuid4()),  primary_key=True, nullable=False, unique=True)
    created_at = mapped_column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = mapped_column(DateTime, default=datetime.now(timezone.utc), nullable=False)

    def __init__(self) -> None:
        self.id = str(uuid4())
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def update(self, **kwargs: dict) -> None:
        """
            Update a set of attributes in an object.
            :params
                @kwargs: a dictionary of attributes
                        to update
        """
        for key, value in kwargs.items():
            setattr(self, key, value)

    def delete(self) -> None:
        """
            :method
                delete: deletes or removes an object from the session and saves.
        """
        g.db_storage.delete(self)
        return g.db_storage.save()

    def add(self) -> None:
        """
            :method
                add: j
        """
        g.db_storage.new(self)

    def save(self) -> None:
        self.updated_at = datetime.now(timezone.utc)
        g.db_storage.new(self)
        return g.db_storage.save()

    def refresh(self):
        g.db_storage.refresh(self)

    @classmethod
    def all(cls):
        return g.db_storage.all(cls)
    
    @classmethod
    def count(cls, **filters: dict) -> int:
        return g.db_storage.count(cls, **filters)
    
    @classmethod
    def search(cls, **filters: dict) -> list:
        return g.db_storage.search(cls, **filters)
    
    def to_dict(self, strip: Optional[List[str]] = None) -> dict:
        dict_repr = copy.deepcopy(self.__dict__)
        if '_sa_instance_state' in dict_repr:
            del dict_repr['_sa_instance_state']
        if strip is not None:
            return {key: value for key, value in dict_repr.items() if key not in strip}
        return dict_repr

    def __repr__(self) -> str:
        attrs = ", ".join([f"{key}={value}" for key, value in self.__dict__.items()])
        return f"{self.__class__.__name__}({attrs})"
