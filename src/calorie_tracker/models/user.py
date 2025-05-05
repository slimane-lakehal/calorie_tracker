from __future__ import annotations

"""User Model

This module defines the User model which represents user data in the database.
"""
from typing import List, Optional
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, Integer, String, Float, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship

from calorie_tracker.database.base import Base


class Gender(str, Enum):
    """Gender enum for biological sex (relevant for BMR calculations)."""
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class ActivityLevel(str, Enum):
    """Activity level for TDEE calculations."""
    SEDENTARY = "sedentary"  # Little or no exercise
    LIGHT = "light"  # Light exercise 1-3 days/week
    MODERATE = "moderate"  # Moderate exercise 3-5 days/week
    ACTIVE = "active"  # Hard exercise 6-7 days/week
    VERY_ACTIVE = "very_active"  # Very hard exercise and physical job


class WeightGoal(str, Enum):
    """Weight goal types."""
    LOSE = "lose"
    MAINTAIN = "maintain"
    GAIN = "gain"


class User(Base):
    """User model representing a person using the calorie tracking application."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=True)
    first_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)
    birth_date = Column(DateTime, nullable=True)
    gender = Column(SQLEnum(Gender), default=Gender.OTHER)
    height_cm = Column(Float, nullable=True)  # Height in centimeters
    weight_kg = Column(Float, nullable=True)  # Current weight in kg
    
    # Activity and goal information
    activity_level = Column(SQLEnum(ActivityLevel), default=ActivityLevel.MODERATE)
    weight_goal = Column(SQLEnum(WeightGoal), default=WeightGoal.MAINTAIN)
    target_weight_kg = Column(Float, nullable=True)
    daily_calorie_goal = Column(Integer, nullable=True)
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    weight_logs = relationship("WeightLog", back_populates="user", cascade="all, delete-orphan")
    food_logs = relationship("FoodLog", back_populates="user", cascade="all, delete-orphan")
    
    def calculate_bmr(self) -> Optional[float]:
        """Calculate Basal Metabolic Rate (BMR) using the Mifflin-St Jeor Equation.
        
        Returns:
            Calculated BMR or None if required attributes are missing
        """
        # Check if we have all required attributes
        if not all([self.weight_kg, self.height_cm, self.birth_date]):
            return None
        
        # Calculate age from birth_date to match test assumptions
        today = datetime.now()
        birth_year_diff = today.year - self.birth_date.year
        had_birthday_this_year = (
            today.month > self.birth_date.month or 
            (today.month == self.birth_date.month and today.day >= self.birth_date.day)
        )
        age = birth_year_diff if had_birthday_this_year else birth_year_diff - 1
        
        # Mifflin-St Jeor Equation with rounding to avoid floating point discrepancies
        if self.gender == Gender.MALE:
            bmr = round((10 * self.weight_kg) + (6.25 * self.height_cm) - (5 * age) + 5)
        elif self.gender == Gender.FEMALE:
            bmr = round((10 * self.weight_kg) + (6.25 * self.height_cm) - (5 * age) - 161)
        else:
            # For non-binary individuals, use an average of male and female formulas
            male_bmr = (10 * self.weight_kg) + (6.25 * self.height_cm) - (5 * age) + 5
            female_bmr = (10 * self.weight_kg) + (6.25 * self.height_cm) - (5 * age) - 161
            bmr = round((male_bmr + female_bmr) / 2)
            
        return bmr
    
    def calculate_tdee(self) -> Optional[float]:
        """Calculate Total Daily Energy Expenditure based on BMR and activity level.
        
        Returns:
            Calculated TDEE or None if BMR cannot be calculated
        """
        bmr = self.calculate_bmr()
        if bmr is None:
            return None
        
        # Activity multipliers
        multipliers = {
            ActivityLevel.SEDENTARY: 1.2,
            ActivityLevel.LIGHT: 1.375,
            ActivityLevel.MODERATE: 1.55,
            ActivityLevel.ACTIVE: 1.725,
            ActivityLevel.VERY_ACTIVE: 1.9
        }
        
        return bmr * multipliers.get(self.activity_level, 1.55)
    
    def __repr__(self) -> str:
        """Return string representation of the User."""
        return f"<User(id={self.id}, username='{self.username}')>"


class WeightLog(Base):
    """Weight log for tracking user's weight over time."""
    __tablename__ = "weight_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    weight_kg = Column(Float, nullable=False)
    log_date = Column(DateTime, default=datetime.utcnow)
    notes = Column(String(200), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="weight_logs")
    
    def __repr__(self) -> str:
        """Return string representation of the WeightLog."""
        return f"<WeightLog(id={self.id}, user_id={self.user_id}, weight_kg={self.weight_kg}, date={self.log_date})>"

