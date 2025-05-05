"""
Calorie Tracker Models Package

This package contains SQLAlchemy ORM models for the application.
"""

# Import all models to ensure they're registered with the Base
from calorie_tracker.models.user import User, WeightLog, Gender, ActivityLevel, WeightGoal
from calorie_tracker.models.food import Food, FoodLog, FoodCategory, MealType

__all__ = [
    'User',
    'WeightLog',
    'Gender',
    'ActivityLevel',
    'WeightGoal',
    'Food',
    'FoodLog',
    'FoodCategory',
    'MealType',
]

