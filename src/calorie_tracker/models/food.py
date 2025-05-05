from __future__ import annotations

"""Food Models

This module defines the food-related models including Food items,
FoodLog for tracking user consumption, and nutritional components.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Table
from sqlalchemy.orm import relationship

from calorie_tracker.database.base import Base


class MealType(str, Enum):
    """Types of meals for categorizing food entries."""
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"
    OTHER = "other"


# Association table for many-to-many relationship between foods and categories
food_category_association = Table(
    "food_category_association",
    Base.metadata,
    Column("food_id", Integer, ForeignKey("foods.id"), primary_key=True),
    Column("category_id", Integer, ForeignKey("food_categories.id"), primary_key=True)
)


class Food(Base):
    """Food model representing a food item in the database."""
    __tablename__ = "foods"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    brand = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    
    # Nutritional information per 100g/ml
    serving_size_g = Column(Float, nullable=False, default=100.0)
    calories = Column(Integer, nullable=False)
    protein_g = Column(Float, nullable=False, default=0.0)
    carbs_g = Column(Float, nullable=False, default=0.0)
    fat_g = Column(Float, nullable=False, default=0.0)
    fiber_g = Column(Float, nullable=True)
    sugar_g = Column(Float, nullable=True)
    sodium_mg = Column(Float, nullable=True)
    
    # System fields
    is_verified = Column(Boolean, default=False)  # Whether nutritional info is verified
    is_custom = Column(Boolean, default=False)  # User-created vs system food
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # If created by a user
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    categories = relationship("FoodCategory", secondary=food_category_association, back_populates="foods")
    food_logs = relationship("FoodLog", back_populates="food")
    
    def calculate_nutrition_for_serving(self, serving_weight_g: float) -> Dict[str, Any]:
        """Calculate nutritional values for a specific serving size.
        
        Args:
            serving_weight_g: Serving weight in grams
            
        Returns:
            Dictionary with scaled nutritional values
        """
        multiplier = serving_weight_g / self.serving_size_g
        
        return {
            "calories": round(self.calories * multiplier),
            "protein_g": round(self.protein_g * multiplier, 1),
            "carbs_g": round(self.carbs_g * multiplier, 1),
            "fat_g": round(self.fat_g * multiplier, 1),
            "fiber_g": round(self.fiber_g * multiplier, 1) if self.fiber_g is not None else None,
            "sugar_g": round(self.sugar_g * multiplier, 1) if self.sugar_g is not None else None,
            "sodium_mg": round(self.sodium_mg * multiplier) if self.sodium_mg is not None else None
        }
    
    def __repr__(self) -> str:
        """Return string representation of the Food."""
        return f"<Food(id={self.id}, name='{self.name}', calories={self.calories})>"


class FoodCategory(Base):
    """Food category for grouping similar food items."""
    __tablename__ = "food_categories"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, unique=True)
    description = Column(String(200), nullable=True)
    
    # Relationships
    foods = relationship("Food", secondary=food_category_association, back_populates="categories")
    
    def __repr__(self) -> str:
        """Return string representation of the FoodCategory."""
        return f"<FoodCategory(id={self.id}, name='{self.name}')>"


class FoodLog(Base):
    """Food log for tracking user's food consumption."""
    __tablename__ = "food_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    food_id = Column(Integer, ForeignKey("foods.id"), nullable=False)
    
    # Consumption details
    meal_type = Column(String(20), nullable=False, default=MealType.OTHER)
    serving_size_g = Column(Float, nullable=False)
    log_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    notes = Column(String(200), nullable=True)
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="food_logs")
    food = relationship("Food", back_populates="food_logs")
    
    @property
    def calories(self) -> int:
        """Calculate calories for the logged serving size."""
        if self.food and self.serving_size_g:
            multiplier = self.serving_size_g / self.food.serving_size_g
            return round(self.food.calories * multiplier)
        return 0
    
    @property
    def protein_g(self) -> float:
        """Calculate protein for the logged serving size."""
        if self.food and self.serving_size_g:
            multiplier = self.serving_size_g / self.food.serving_size_g
            return round(self.food.protein_g * multiplier, 1)
        return 0.0
    
    @property
    def carbs_g(self) -> float:
        """Calculate carbohydrates for the logged serving size."""
        if self.food and self.serving_size_g:
            multiplier = self.serving_size_g / self.food.serving_size_g
            return round(self.food.carbs_g * multiplier, 1)
        return 0.0
    
    @property
    def fat_g(self) -> float:
        """Calculate fat for the logged serving size."""
        if self.food and self.serving_size_g:
            multiplier = self.serving_size_g / self.food.serving_size_g
            return round(self.food.fat_g * multiplier, 1)
        return 0.0
    
    def get_nutrition_data(self) -> Dict[str, Any]:
        """Get complete nutrition data for this food log entry.
        
        Returns:
            Dictionary with nutritional values for the logged serving
        """
        if self.food is None:
            return {}
            
        return self.food.calculate_nutrition_for_serving(self.serving_size_g)
    
    def __repr__(self) -> str:
        """Return string representation of the FoodLog."""
        return f"<FoodLog(id={self.id}, user_id={self.user_id}, food_id={self.food_id}, calories={self.calories})>"
