from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import db
import secrets
import string


class City(db.Model):
    __tablename__ = 'cities'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    
    # Relationships
    objects = relationship('Object', back_populates='city', cascade='all, delete-orphan')
    form_submissions = relationship('FormSubmission', back_populates='city')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name
        }


class Object(db.Model):
    __tablename__ = 'objects'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    city_id = Column(Integer, ForeignKey('cities.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(200), nullable=False)
    
    # Relationships
    city = relationship('City', back_populates='objects')
    form_submissions = relationship('FormSubmission', back_populates='object')
    
    def to_dict(self):
        return {
            'id': self.id,
            'city_id': self.city_id,
            'name': self.name
        }


class ViolationCategory(db.Model):
    __tablename__ = 'violation_categories'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    
    # Relationships
    violations = relationship('Violation', back_populates='category', cascade='all, delete-orphan')
    form_submissions = relationship('FormSubmission', back_populates='violation_category')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name
        }


class Violation(db.Model):
    __tablename__ = 'violations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(Integer, ForeignKey('violation_categories.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(200), nullable=False)
    
    # Relationships
    category = relationship('ViolationCategory', back_populates='violations')
    form_submissions = relationship('FormSubmission', back_populates='violation')
    
    def to_dict(self):
        return {
            'id': self.id,
            'category_id': self.category_id,
            'name': self.name
        }


class FormSubmission(db.Model):
    __tablename__ = 'form_submissions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    city_id = Column(Integer, ForeignKey('cities.id', ondelete='RESTRICT'), nullable=False)
    object_id = Column(Integer, ForeignKey('objects.id', ondelete='RESTRICT'), nullable=False)
    violation_category_id = Column(Integer, ForeignKey('violation_categories.id', ondelete='RESTRICT'), nullable=False)
    violation_id = Column(Integer, ForeignKey('violations.id', ondelete='RESTRICT'), nullable=False)
    comment = Column(Text, nullable=True)
    file_path = Column(String(500), nullable=True)
    telegram_user_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    # Relationships
    city = relationship('City', back_populates='form_submissions')
    object = relationship('Object', back_populates='form_submissions')
    violation_category = relationship('ViolationCategory', back_populates='form_submissions')
    violation = relationship('Violation', back_populates='form_submissions')
    
    def to_dict(self):
        return {
            'id': self.id,
            'city_id': self.city_id,
            'object_id': self.object_id,
            'violation_category_id': self.violation_category_id,
            'violation_id': self.violation_id,
            'comment': self.comment,
            'file_path': self.file_path,
            'telegram_user_id': self.telegram_user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class User(db.Model):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    tg_id = Column(Integer, nullable=False, unique=True)  # Telegram user ID
    secret_key = Column(String(64), nullable=False, unique=True)  # Secret key for external system
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'tg_id': self.tg_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @staticmethod
    def generate_secret_key():
        """Generate a random secret key for the user"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(32))


