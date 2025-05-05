import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from calorie_tracker.database.base import Base
from calorie_tracker.models.user import User, Gender, ActivityLevel, WeightGoal, WeightLog


@pytest.fixture
def engine():
    """Create a SQLite in-memory database engine for testing."""
    return create_engine("sqlite:///:memory:")


@pytest.fixture
def session(engine):
    """Create a new database session for testing."""
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def complete_user():
    """Create a user with all required attributes for BMR/TDEE calculation."""
    # Calculate birth date for exactly 30 years old
    today = datetime.now()
    birth_date = datetime(today.year - 30, today.month, today.day)
    
    return User(
        username="testuser",
        email="test@example.com",
        first_name="Test",
        last_name="User",
        birth_date=birth_date,  # Exactly 30 years old
        gender=Gender.MALE,
        height_cm=180.0,
        weight_kg=80.0,
        activity_level=ActivityLevel.MODERATE,
        weight_goal=WeightGoal.MAINTAIN,
        target_weight_kg=75.0,
        daily_calorie_goal=2500
    )


@pytest.fixture
def incomplete_user():
    """Create a user with missing attributes for BMR/TDEE calculation."""
    return User(
        username="incompleteuser",
        email="incomplete@example.com",
        first_name="Incomplete",
        gender=Gender.FEMALE
        # Missing height, weight, and birth_date
    )


class TestUserModel:
    """Test the User model."""

    def test_user_creation(self, session, complete_user):
        """Test creating a user and saving to the database."""
        session.add(complete_user)
        session.commit()
        
        stored_user = session.query(User).filter_by(username="testuser").first()
        assert stored_user is not None
        assert stored_user.username == "testuser"
        assert stored_user.email == "test@example.com"
        assert stored_user.first_name == "Test"
        assert stored_user.last_name == "User"
        assert stored_user.gender == Gender.MALE
        assert stored_user.height_cm == 180.0
        assert stored_user.weight_kg == 80.0
        assert stored_user.activity_level == ActivityLevel.MODERATE
        assert stored_user.weight_goal == WeightGoal.MAINTAIN
        assert stored_user.target_weight_kg == 75.0
        assert stored_user.daily_calorie_goal == 2500

    def test_user_representation(self, complete_user):
        """Test the string representation of a user."""
        # Since id will be None before adding to session
        assert repr(complete_user) == "<User(id=None, username='testuser')>"

    def test_calculate_bmr_male(self, complete_user):
        """Test BMR calculation for a male user."""
        # Calculate expected BMR using the Mifflin-St Jeor Equation for males
        # BMR = (10 * weight) + (6.25 * height) - (5 * age) + 5
        age = 30
        expected_bmr = round((10 * 80.0) + (6.25 * 180.0) - (5 * age) + 5)
        # Allow for small floating-point differences
        assert abs(complete_user.calculate_bmr() - expected_bmr) < 0.1

    def test_calculate_bmr_female(self, complete_user):
        """Test BMR calculation for a female user."""
        complete_user.gender = Gender.FEMALE
        
        # Calculate expected BMR using the Mifflin-St Jeor Equation for females
        # BMR = (10 * weight) + (6.25 * height) - (5 * age) - 161
        age = 30
        expected_bmr = round((10 * 80.0) + (6.25 * 180.0) - (5 * age) - 161)
        
        # Allow for small floating-point differences
        assert abs(complete_user.calculate_bmr() - expected_bmr) < 0.1

    def test_calculate_bmr_other(self, complete_user):
        """Test BMR calculation for a non-binary user."""
        complete_user.gender = Gender.OTHER
        
        # Calculate expected BMR as average of male and female formulas
        age = 30
        male_bmr = (10 * 80.0) + (6.25 * 180.0) - (5 * age) + 5
        female_bmr = (10 * 80.0) + (6.25 * 180.0) - (5 * age) - 161
        expected_bmr = round((male_bmr + female_bmr) / 2)
        
        # Allow for small floating-point differences
        assert abs(complete_user.calculate_bmr() - expected_bmr) < 0.1

    def test_calculate_bmr_missing_data(self, incomplete_user):
        """Test BMR calculation when required data is missing."""
        assert incomplete_user.calculate_bmr() is None

    def test_calculate_tdee_different_activity_levels(self, complete_user):
        """Test TDEE calculation with different activity levels."""
        # Calculate base BMR
        bmr = complete_user.calculate_bmr()
        
        # Test SEDENTARY
        complete_user.activity_level = ActivityLevel.SEDENTARY
        assert abs(complete_user.calculate_tdee() - (bmr * 1.2)) < 0.1
        
        # Test LIGHT
        complete_user.activity_level = ActivityLevel.LIGHT
        assert abs(complete_user.calculate_tdee() - (bmr * 1.375)) < 0.1
        
        # Test MODERATE
        complete_user.activity_level = ActivityLevel.MODERATE
        assert abs(complete_user.calculate_tdee() - (bmr * 1.55)) < 0.1
        
        # Test ACTIVE
        complete_user.activity_level = ActivityLevel.ACTIVE
        assert abs(complete_user.calculate_tdee() - (bmr * 1.725)) < 0.1
        
        # Test VERY_ACTIVE
        complete_user.activity_level = ActivityLevel.VERY_ACTIVE
        assert abs(complete_user.calculate_tdee() - (bmr * 1.9)) < 0.1

    def test_calculate_tdee_missing_data(self, incomplete_user):
        """Test TDEE calculation when required data is missing."""
        assert incomplete_user.calculate_tdee() is None

    def test_weight_log_relationship(self, session, complete_user):
        """Test the relationship between User and WeightLog."""
        # Add user to session
        session.add(complete_user)
        session.commit()
        
        # Create weight logs
        log1 = WeightLog(
            user_id=complete_user.id,
            weight_kg=80.0,
            log_date=datetime.utcnow() - timedelta(days=30),
            notes="Initial weight"
        )
        
        log2 = WeightLog(
            user_id=complete_user.id,
            weight_kg=79.5,
            log_date=datetime.utcnow() - timedelta(days=15),
            notes="Progress check"
        )
        
        log3 = WeightLog(
            user_id=complete_user.id,
            weight_kg=78.8,
            log_date=datetime.utcnow(),
            notes="Current weight"
        )
        
        # Add weight logs to session
        session.add_all([log1, log2, log3])
        session.commit()
        
        # Refresh user from database to ensure relationships are loaded
        session.refresh(complete_user)
        
        # Test weight_logs relationship
        assert len(complete_user.weight_logs) == 3
        assert complete_user.weight_logs[0].weight_kg == 80.0
        assert complete_user.weight_logs[1].weight_kg == 79.5
        assert complete_user.weight_logs[2].weight_kg == 78.8
        
        # Test cascading delete
        session.delete(complete_user)
        session.commit()
        
        # Verify all weight logs are deleted
        assert session.query(WeightLog).count() == 0

