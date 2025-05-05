"""CLI Interface for Calorie Tracker

This module provides a command-line interface for the calorie tracking application
using the Click library.
"""
from __future__ import annotations
from typing import Optional
import sys
import os
import click
from datetime import datetime, date, timedelta
from calorie_tracker.database.base import init_db, get_db_session, get_engine
from calorie_tracker.models.user import User, Gender, ActivityLevel, WeightGoal, WeightLog
from calorie_tracker.models.food import Food, FoodLog, MealType, FoodCategory


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Calorie Tracker - A comprehensive tool for tracking calories and managing fitness goals."""
    # Ensure the database is initialized
    try:
        init_db()
    except Exception as e:
        click.echo(f"Error initializing database: {e}", err=True)
        sys.exit(1)


# User management commands
@cli.group()
def user():
    """User profile management commands."""
    pass


@user.command("create")
@click.option("--username", prompt=True, help="Unique username for identification")
@click.option("--email", help="Email address")
@click.option("--first-name", help="First name")
@click.option("--last-name", help="Last name")
@click.option("--birth-date", type=click.DateTime(formats=["%Y-%m-%d"]), help="Birth date (YYYY-MM-DD)")
@click.option("--gender", type=click.Choice(["male", "female", "other"]), default="other", help="Gender for BMR calculations")
@click.option("--height-cm", type=float, help="Height in centimeters")
@click.option("--weight-kg", type=float, help="Current weight in kilograms")
@click.option("--activity-level", type=click.Choice(["sedentary", "light", "moderate", "active", "very_active"]), 
              default="moderate", help="Activity level for TDEE calculations")
@click.option("--weight-goal", type=click.Choice(["lose", "maintain", "gain"]), default="maintain", 
              help="Weight management goal")
@click.option("--target-weight-kg", type=float, help="Target weight in kilograms")
def create_user(username, email, first_name, last_name, birth_date, gender, 
                height_cm, weight_kg, activity_level, weight_goal, target_weight_kg):
    """Create a new user profile."""
    try:
        with get_db_session() as session:
            # Check if username already exists
            existing_user = session.query(User).filter(User.username == username).first()
            if existing_user:
                click.echo(f"Error: Username '{username}' already exists", err=True)
                return
            
            # Create new user
            user = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                birth_date=birth_date,
                gender=Gender(gender) if gender else None,
                height_cm=height_cm,
                weight_kg=weight_kg,
                activity_level=ActivityLevel(activity_level) if activity_level else None,
                weight_goal=WeightGoal(weight_goal) if weight_goal else None,
                target_weight_kg=target_weight_kg
            )
            
            # Calculate and set daily calorie goal if possible
            if user.calculate_tdee() is not None:
                tdee = user.calculate_tdee()
                # Set calorie goal based on weight goal
                if user.weight_goal == WeightGoal.LOSE:
                    user.daily_calorie_goal = int(tdee * 0.8)  # 20% deficit
                elif user.weight_goal == WeightGoal.GAIN:
                    user.daily_calorie_goal = int(tdee * 1.15)  # 15% surplus
                else:  # MAINTAIN
                    user.daily_calorie_goal = int(tdee)
            
            session.add(user)
            session.commit()
            
            # Add initial weight log if weight provided
            if weight_kg:
                weight_log = WeightLog(
                    user_id=user.id,
                    weight_kg=weight_kg,
                    log_date=datetime.utcnow(),
                    notes="Initial weight"
                )
                session.add(weight_log)
                session.commit()
            
            click.echo(f"User '{username}' created successfully!")
            if user.daily_calorie_goal:
                click.echo(f"Daily calorie goal set to {user.daily_calorie_goal} calories")
    
    except Exception as e:
        click.echo(f"Error creating user: {e}", err=True)


@user.command("list")
def list_users():
    """List all user profiles."""
    try:
        with get_db_session() as session:
            users = session.query(User).all()
            
            if not users:
                click.echo("No users found")
                return
                
            click.echo("\nUser Profiles:")
            click.echo("-" * 80)
            for user in users:
                click.echo(f"ID: {user.id} | Username: {user.username} | Name: {user.first_name} {user.last_name}")
                if user.daily_calorie_goal:
                    click.echo(f"  Daily calorie goal: {user.daily_calorie_goal} calories")
                if user.weight_kg:
                    click.echo(f"  Current weight: {user.weight_kg:.1f} kg")
                if user.target_weight_kg:
                    click.echo(f"  Target weight: {user.target_weight_kg:.1f} kg")
                click.echo("-" * 80)
    
    except Exception as e:
        click.echo(f"Error listing users: {e}", err=True)


@user.command("info")
@click.argument("username")
def user_info(username):
    """Show detailed information for a specific user."""
    try:
        with get_db_session() as session:
            user = session.query(User).filter(User.username == username).first()
            
            if not user:
                click.echo(f"User '{username}' not found", err=True)
                return
                
            click.echo("\nUser Profile Details:")
            click.echo("-" * 80)
            click.echo(f"ID: {user.id}")
            click.echo(f"Username: {user.username}")
            click.echo(f"Name: {user.first_name or ''} {user.last_name or ''}")
            click.echo(f"Email: {user.email or 'Not provided'}")
            
            if user.birth_date:
                age = datetime.now().year - user.birth_date.year
                if datetime.now().month < user.birth_date.month or (
                    datetime.now().month == user.birth_date.month and 
                    datetime.now().day < user.birth_date.day
                ):
                    age -= 1
                click.echo(f"Age: {age}")
            
            click.echo(f"Gender: {user.gender.value if user.gender else 'Not provided'}")
            click.echo(f"Height: {user.height_cm or 'Not provided'} cm")
            click.echo(f"Current weight: {user.weight_kg or 'Not provided'} kg")
            click.echo(f"Activity level: {user.activity_level.value if user.activity_level else 'Not provided'}")
            click.echo(f"Weight goal: {user.weight_goal.value if user.weight_goal else 'Not provided'}")
            click.echo(f"Target weight: {user.target_weight_kg or 'Not provided'} kg")
            
            # Display calculated metrics
            if user.calculate_bmr() is not None:
                click.echo(f"BMR: {user.calculate_bmr():.0f} calories/day")
            if user.calculate_tdee() is not None:
                click.echo(f"TDEE: {user.calculate_tdee():.0f} calories/day")
            
            click.echo(f"Daily calorie goal: {user.daily_calorie_goal or 'Not set'} calories")
            click.echo("-" * 80)
            
            # Show recent weight logs if available
            weight_logs = (
                session.query(WeightLog)
                .filter(WeightLog.user_id == user.id)
                .order_by(WeightLog.log_date.desc())
                .limit(5)
                .all()
            )
            
            if weight_logs:
                click.echo("\nRecent Weight Logs:")
                click.echo("-" * 80)
                for log in weight_logs:
                    click.echo(f"Date: {log.log_date.strftime('%Y-%m-%d')} | Weight: {log.weight_kg:.1f} kg")
                click.echo("-" * 80)
    
    except Exception as e:
        click.echo(f"Error displaying user info: {e}", err=True)


# Food logging commands
@cli.group()
def food():
    """Food and meal management commands."""
    pass


@food.command("add")
@click.option("--name", prompt=True, help="Name of the food item")
@click.option("--brand", help="Brand name (if applicable)")
@click.option("--calories", type=int, prompt=True, help="Calories per serving")
@click.option("--protein", type=float, default=0, help="Protein in grams")
@click.option("--carbs", type=float, default=0, help="Carbohydrates in grams")
@click.option("--fat", type=float, default=0, help="Fat in grams")
@click.option("--fiber", type=float, help="Fiber in grams")
@click.option("--sugar", type=float, help="Sugar in grams")
@click.option("--serving-size", type=float, default=100.0, help="Serving size in grams")
@click.option("--description", help="Description of the food")
@click.option("--category", help="Food category")
def add_food(name, brand, calories, protein, carbs, fat, fiber, sugar, serving_size, description, category):
    """Add a new food item to the database."""
    try:
        with get_db_session() as session:
            # Check if food already exists with same name and brand
            existing_food = (
                session.query(Food)
                .filter(Food.name == name)
                .filter(Food.brand == brand if brand else Food.brand.is_(None))
                .first()
            )
            
            if existing_food:
                click.echo(f"Warning: Similar food already exists (ID: {existing_food.id})")
                if not click.confirm("Do you want to continue adding this food?"):
                    return
            
            # Create new food item
            food = Food(
                name=name,
                brand=brand,
                description=description,
                serving_size_g=serving_size,
                calories=calories,
                protein_g=protein,
                carbs_g=carbs,
                fat_g=fat,
                fiber_g=fiber,
                sugar_g=sugar,
                is_custom=True
            )
            
            # Add category if provided
            if category:
                existing_category = session.query(FoodCategory).filter(FoodCategory.name == category).first()
                if not existing_category:
                    existing_category = FoodCategory(name=category)
                    session.add(existing_category)
                
                food.categories.append(existing_category)
            
            session.add(food)
            session.commit()
            
            click.echo(f"Food '{name}' added successfully with ID: {food.id}")
    
    except Exception as e:
        click.echo(f"Error adding food: {e}", err=True)


@food.command("list")
@click.option("--category", help="Filter by category")
@click.option("--query", help="Search by name or description")
@click.option("--limit", type=int, default=20, help="Maximum number of results")
def list_foods(category, query, limit):
    """List food items in the database."""
    try:
        with get_db_session() as session:
            # Build query
            foods_query = session.query(Food)
            
            if category:
                category_obj = session.query(FoodCategory).filter(FoodCategory.name == category).first()
                if category_obj:
                    foods_query = foods_query.filter(Food.categories.contains(category_obj))
                else:
                    click.echo(f"Warning: Category '{category}' not found", err=True)
            
            if query:
                # Search by name or description
                search_term = f"%{query}%"  # For LIKE query
                foods_query = foods_query.filter(
                    (Food.name.ilike(search_term)) | 
                    (Food.description.ilike(search_term)) |
                    (Food.brand.ilike(search_term))
                )
            
            # Apply limit and get results
            foods = foods_query.limit(limit).all()
            
            if not foods:
                click.echo("No matching food items found")
                return
                
            click.echo("\nFood Items:")
            click.echo("-" * 90)
            click.echo(f"{'ID':>4} | {'Name':<25} | {'Brand':<15} | {'Calories':>8} | {'Protein':>7} | {'Carbs':>7} | {'Fat':>7}")
            click.echo("-" * 90)
            
            for food in foods:
                # Format brand or use empty string if None
                brand_display = food.brand or ""
                
                click.echo(
                    f"{food.id:4d} | "
                    f"{food.name[:25]:<25} | "
                    f"{brand_display[:15]:<15} | "
                    f"{food.calories:8d} | "
                    f"{food.protein_g:7.1f} | "
                    f"{food.carbs_g:7.1f} | "
                    f"{food.fat_g:7.1f}"
                )
                
            click.echo("-" * 90)
            if len(foods) == limit:
                click.echo(f"Showing first {limit} results. Use --limit option to see more.")
    
    except Exception as e:
        click.echo(f"Error listing foods: {e}", err=True)


@food.command("info")
@click.argument("food_id", type=int)
def food_info(food_id):
    """Show detailed information for a specific food."""
    try:
        with get_db_session() as session:
            food = session.query(Food).filter(Food.id == food_id).first()
            
            if not food:
                click.echo(f"Food with ID {food_id} not found", err=True)
                return
                
            click.echo("\nFood Details:")
            click.echo("-" * 80)
            click.echo(f"ID: {food.id}")
            click.echo(f"Name: {food.name}")
            
            if food.brand:
                click.echo(f"Brand: {food.brand}")
                
            if food.description:
                click.echo(f"Description: {food.description}")
                
            # Display categories if any
            if food.categories:
                categories = ", ".join([category.name for category in food.categories])
                click.echo(f"Categories: {categories}")
            
            click.echo("\nNutritional Information (per 100g unless specified):")
            click.echo(f"Serving Size: {food.serving_size_g}g")
            click.echo(f"Calories: {food.calories}")
            click.echo(f"Protein: {food.protein_g}g")
            click.echo(f"Carbohydrates: {food.carbs_g}g")
            click.echo(f"Fat: {food.fat_g}g")
            
            if food.fiber_g is not None:
                click.echo(f"Fiber: {food.fiber_g}g")
                
            if food.sugar_g is not None:
                click.echo(f"Sugar: {food.sugar_g}g")
                
            if food.sodium_mg is not None:
                click.echo(f"Sodium: {food.sodium_mg}mg")
            
            click.echo("-" * 80)
    
    except Exception as e:
        click.echo(f"Error displaying food info: {e}", err=True)


# Food logging commands
@cli.group()
def log():
    """Food logging and tracking commands."""
    pass


@log.command("meal")
@click.option("--username", prompt=True, help="Username of the person logging food")
@click.option("--food-id", type=int, prompt=True, help="ID of the food item")
@click.option("--serving-size", type=float, prompt=True, help="Serving size in grams")
@click.option("--meal-type", 
              type=click.Choice(["breakfast", "lunch", "dinner", "snack", "other"]),
              default="other", 
              help="Type of meal")
@click.option("--date", type=click.DateTime(formats=["%Y-%m-%d"]), 
              default=lambda: datetime.now().strftime("%Y-%m-%d"),
              help="Date of consumption (YYYY-MM-DD), defaults to today")
@click.option("--notes", help="Additional notes about this meal")
def log_meal(username, food_id, serving_size, meal_type, date, notes):
    """Log a meal for a user."""
    try:
        with get_db_session() as session:
            # Verify user exists
            user = session.query(User).filter(User.username == username).first()
            if not user:
                click.echo(f"User '{username}' not found", err=True)
                return
            
            # Verify food exists
            food = session.query(Food).filter(Food.id == food_id).first()
            if not food:
                click.echo(f"Food with ID {food_id} not found", err=True)
                return
            
            # Create food log entry
            food_log = FoodLog(
                user_id=user.id,
                food_id=food.id,
                meal_type=meal_type,
                serving_size_g=serving_size,
                log_date=date,
                notes=notes
            )
            
            session.add(food_log)
            session.commit()
            
            # Calculate nutritional information for this serving
            nutrition = food.calculate_nutrition_for_serving(serving_size)
            
            click.echo(f"\nMeal logged successfully!")
            click.echo(f"Food: {food.name}")
            click.echo(f"Serving: {serving_size}g")
            click.echo(f"Calories: {nutrition['calories']}")
            click.echo(f"Protein: {nutrition['protein_g']}g")
            click.echo(f"Carbs: {nutrition['carbs_g']}g")
            click.echo(f"Fat: {nutrition['fat_g']}g")
    
    except Exception as e:
        click.echo(f"Error logging meal: {e}", err=True)


@log.command("list")
@click.option("--username", prompt=True, help="Username to view logs for")
@click.option("--date", type=click.DateTime(formats=["%Y-%m-%d"]), 
              default=lambda: datetime.now().strftime("%Y-%m-%d"),
              help="Date to view logs for (YYYY-MM-DD), defaults to today")
@click.option("--meal-type", 
              type=click.Choice(["breakfast", "lunch", "dinner", "snack", "other"]),
              help="Filter by meal type")
def list_logs(username, date, meal_type):
    """List food logs for a user on a specific date."""
    try:
        with get_db_session() as session:
            # Verify user exists
            user = session.query(User).filter(User.username == username).first()
            if not user:
                click.echo(f"User '{username}' not found", err=True)
                return
            
            # Query food logs
            log_query = (
                session.query(FoodLog)
                .filter(FoodLog.user_id == user.id)
                .join(Food)  # Join with Food to access food details
            )
            
            # Apply date filter: match logs for the same day
            # Extract date components for comparison
            date_start = datetime(date.year, date.month, date.day, 0, 0, 0)
            date_end = datetime(date.year, date.month, date.day, 23, 59, 59)
            log_query = log_query.filter(FoodLog.log_date.between(date_start, date_end))
            
            # Apply meal type filter if specified
            if meal_type:
                log_query = log_query.filter(FoodLog.meal_type == meal_type)
            
            # Order by meal type and time
            logs = log_query.order_by(FoodLog.meal_type, FoodLog.log_date).all()
            
            if not logs:
                click.echo(f"No food logs found for {username} on {date.strftime('%Y-%m-%d')}")
                return
            
            # Display log summary
            date_str = date.strftime("%Y-%m-%d")
            click.echo(f"\nFood Logs for {username} on {date_str}:")
            click.echo("-" * 90)
            
            # Initialize counters for daily totals
            total_calories = 0
            total_protein = 0
            total_carbs = 0
            total_fat = 0
            
            # Group logs by meal type
            current_meal = None
            
            for log in logs:
                # Print meal type header when it changes
                if current_meal != log.meal_type:
                    current_meal = log.meal_type
                    click.echo(f"\n{current_meal.upper()}:")
                    click.echo(f"{'Food':<30} | {'Serving':<10} | {'Calories':>8} | {'Protein':>7} | {'Carbs':>7} | {'Fat':>7}")
                    click.echo("-" * 90)
                
                # Calculate nutrition for this log entry
                calories = log.calories
                protein = log.protein_g
                carbs = log.carbs_g
                fat = log.fat_g
                
                # Add to daily totals
                total_calories += calories
                total_protein += protein
                total_carbs += carbs
                total_fat += fat
                
                # Display the log entry
                click.echo(
                    f"{log.food.name[:30]:<30} | "
                    f"{log.serving_size_g:10.1f}g | "
                    f"{calories:8d} | "
                    f"{protein:7.1f}g | "
                    f"{carbs:7.1f}g | "
                    f"{fat:7.1f}g"
                )
            
            # Display daily totals
            click.echo("\nDAILY TOTALS:")
            click.echo("-" * 90)
            click.echo(
                f"{'Total':<30} | {'':10} | "
                f"{total_calories:8d} | "
                f"{total_protein:7.1f}g | "
                f"{total_carbs:7.1f}g | "
                f"{total_fat:7.1f}g"
            )
            click.echo("-" * 90)
            
            # Display comparison to daily goals if available
            if user.daily_calorie_goal:
                remaining = user.daily_calorie_goal - total_calories
                percent = (total_calories / user.daily_calorie_goal) * 100 if user.daily_calorie_goal else 0
                
                click.echo(f"\nCalorie Goal: {user.daily_calorie_goal}")
                click.echo(f"Calories Consumed: {total_calories} ({percent:.1f}%)")
                
                if remaining > 0:
                    click.echo(f"Remaining: {remaining} calories")
                else:
                    click.echo(f"Exceeded by: {abs(remaining)} calories")
    
    except Exception as e:
        click.echo(f"Error listing food logs: {e}", err=True)


@log.command("summary")
@click.option("--username", prompt=True, help="Username to view summary for")
@click.option("--days", type=int, default=7, help="Number of days to include in summary")
@click.option("--show-details", is_flag=True, help="Show detailed daily breakdown")
def log_summary(username, days, show_details):
    """Show a summary of food logs over a period of days."""
    try:
        with get_db_session() as session:
            # Verify user exists
            user = session.query(User).filter(User.username == username).first()
            if not user:
                click.echo(f"User '{username}' not found", err=True)
                return
            
            # Calculate date range for the query
            end_date = datetime.now()
            start_date = datetime(end_date.year, end_date.month, end_date.day) - \
                        timedelta(days=days-1)
            
            # Query food logs for the specified period
            logs_query = (
                session.query(FoodLog)
                .filter(FoodLog.user_id == user.id)
                .filter(FoodLog.log_date >= start_date)
                .filter(FoodLog.log_date <= end_date)
                .join(Food)
                .order_by(FoodLog.log_date)
            )
            
            logs = logs_query.all()
            
            if not logs:
                click.echo(f"No food logs found for {username} in the last {days} days")
                return
            
            # Group logs by date
            logs_by_date = {}
            for log in logs:
                date_key = log.log_date.strftime("%Y-%m-%d")
                if date_key not in logs_by_date:
                    logs_by_date[date_key] = []
                logs_by_date[date_key].append(log)
            
            # Calculate daily totals and store in a list for analysis
            daily_totals = []
            date_range = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") 
                          for i in range(days)]
            
            click.echo(f"\nFood Log Summary for {username} - Last {days} Days:")
            click.echo("-" * 100)
            
            # Display daily breakdown if requested
            if show_details:
                click.echo(f"{'Date':<12} | {'Calories':>8} | {'Protein':>7} | {'Carbs':>7} | {'Fat':>7} | {'% Goal':>7} | {'Logs':>5}")
                click.echo("-" * 100)
            
            # Process each day in the range
            for date_str in date_range:
                day_logs = logs_by_date.get(date_str, [])
                
                # Calculate totals for this day
                day_calories = sum(log.calories for log in day_logs)
                day_protein = sum(log.protein_g for log in day_logs)
                day_carbs = sum(log.carbs_g for log in day_logs)
                day_fat = sum(log.fat_g for log in day_logs)
                log_count = len(day_logs)
                
                # Calculate percentage of daily goal
                goal_percent = 0
                if user.daily_calorie_goal:
                    goal_percent = (day_calories / user.daily_calorie_goal) * 100
                
                # Store data for overall analysis
                daily_totals.append({
                    "date": date_str,
                    "calories": day_calories,
                    "protein": day_protein,
                    "carbs": day_carbs,
                    "fat": day_fat,
                    "goal_percent": goal_percent,
                    "log_count": log_count
                })
                
                # Display daily data if detailed view is requested
                if show_details:
                    click.echo(
                        f"{date_str:<12} | "
                        f"{day_calories:8d} | "
                        f"{day_protein:7.1f}g | "
                        f"{day_carbs:7.1f}g | "
                        f"{day_fat:7.1f}g | "
                        f"{goal_percent:7.1f}% | "
                        f"{log_count:5d}"
                    )
            
            if show_details:
                click.echo("-" * 100)
            
            # Calculate overall statistics
            days_with_logs = sum(1 for d in daily_totals if d["log_count"] > 0)
            
            if days_with_logs == 0:
                click.echo("No food logs recorded in the selected period.")
                return
            
            total_calories = sum(d["calories"] for d in daily_totals)
            total_protein = sum(d["protein"] for d in daily_totals)
            total_carbs = sum(d["carbs"] for d in daily_totals)
            total_fat = sum(d["fat"] for d in daily_totals)
            
            avg_calories = total_calories / days_with_logs
            avg_protein = total_protein / days_with_logs
            avg_carbs = total_carbs / days_with_logs
            avg_fat = total_fat / days_with_logs
            
            # Calculate average goal achievement
            if user.daily_calorie_goal:
                avg_goal_percent = (avg_calories / user.daily_calorie_goal) * 100
            else:
                avg_goal_percent = 0
            
            # Display overall summary
            click.echo("\nSUMMARY STATISTICS:")
            click.echo("-" * 100)
            click.echo(f"Days with logs: {days_with_logs} out of {days}")
            click.echo(f"Average daily calories: {avg_calories:.0f}")
            
            if user.daily_calorie_goal:
                click.echo(f"Daily calorie goal: {user.daily_calorie_goal}")
                click.echo(f"Average goal achievement: {avg_goal_percent:.1f}%")
            
            # Display macronutrient breakdown
            click.echo("\nAverage Macronutrient Breakdown:")
            click.echo(f"Protein: {avg_protein:.1f}g ({(avg_protein * 4 / avg_calories) * 100 if avg_calories else 0:.1f}% of calories)")
            click.echo(f"Carbs: {avg_carbs:.1f}g ({(avg_carbs * 4 / avg_calories) * 100 if avg_calories else 0:.1f}% of calories)")
            click.echo(f"Fat: {avg_fat:.1f}g ({(avg_fat * 9 / avg_calories) * 100 if avg_calories else 0:.1f}% of calories)")
            
            # Identify trends (simple trend analysis)
            if len(daily_totals) >= 3 and days_with_logs >= 3:
                # Look at the trend in the last few days
                recent_totals = [d for d in daily_totals if d["log_count"] > 0][-3:]
                if len(recent_totals) == 3:
                    cal_trend = recent_totals[2]["calories"] - recent_totals[0]["calories"]
                    
                    click.echo("\nRecent Trends:")
                    if abs(cal_trend) < 50:
                        click.echo("Calorie intake has been stable over recent days.")
                    elif cal_trend > 0:
                        click.echo(f"Calorie intake has increased by {cal_trend} over recent days.")
                    else:
                        click.echo(f"Calorie intake has decreased by {abs(cal_trend)} over recent days.")
                    
                    # Check if user is meeting their goal
                    if user.daily_calorie_goal:
                        recent_avg = sum(d["calories"] for d in recent_totals) / len(recent_totals)
                        diff_from_goal = recent_avg - user.daily_calorie_goal
                        
                        if abs(diff_from_goal) < 50:
                            click.echo("You're consistently meeting your calorie goal!")
                        elif diff_from_goal > 0:
                            click.echo(f"You're averaging {diff_from_goal:.0f} calories above your goal.")
                        else:
                            click.echo(f"You're averaging {abs(diff_from_goal):.0f} calories below your goal.")
            
            # Display weight change if weight logs are available
            weight_logs = (
                session.query(WeightLog)
                .filter(WeightLog.user_id == user.id)
                .filter(WeightLog.log_date >= start_date)
                .filter(WeightLog.log_date <= end_date)
                .order_by(WeightLog.log_date)
                .all()
            )
            
            if len(weight_logs) >= 2:
                first_weight = weight_logs[0].weight_kg
                last_weight = weight_logs[-1].weight_kg
                weight_change = last_weight - first_weight
                
                click.echo("\nWeight Change:")
                if abs(weight_change) < 0.1:
                    click.echo("Your weight has remained stable during this period.")
                elif weight_change > 0:
                    click.echo(f"You've gained {weight_change:.1f} kg during this period.")
                else:
                    click.echo(f"You've lost {abs(weight_change):.1f} kg during this period.")
    
    except Exception as e:
        click.echo(f"Error generating summary: {e}", err=True)


# Export commands
@cli.group()
def export():
    """Export data from the calorie tracker."""
    pass


@export.command("logs")
@click.option("--username", prompt=True, help="Username to export logs for")
@click.option("--format", type=click.Choice(["csv", "json"]), default="csv", 
              help="Export format")
@click.option("--days", type=int, default=30, help="Number of days to include")
@click.option("--output", type=click.Path(), help="Output file path")
def export_logs(username, format, days, output):
    """Export food logs to CSV or JSON format."""
    try:
        with get_db_session() as session:
            # Verify user exists
            user = session.query(User).filter(User.username == username).first()
            if not user:
                click.echo(f"User '{username}' not found", err=True)
                return
            
            # Calculate date range
            end_date = datetime.now()
            start_date = datetime(end_date.year, end_date.month, end_date.day) - \
                        timedelta(days=days-1)
            
            # Query food logs for the period
            logs = (
                session.query(FoodLog)
                .filter(FoodLog.user_id == user.id)
                .filter(FoodLog.log_date >= start_date)
                .filter(FoodLog.log_date <= end_date)
                .join(Food)
                .order_by(FoodLog.log_date)
                .all()
            )
            
            if not logs:
                click.echo(f"No food logs found for {username} in the specified period")
                return
            
            # Prepare export data
            export_data = []
            for log in logs:
                export_data.append({
                    "date": log.log_date.strftime("%Y-%m-%d"),
                    "time": log.log_date.strftime("%H:%M:%S"),
                    "meal_type": log.meal_type,
                    "food_name": log.food.name,
                    "food_brand": log.food.brand,
                    "serving_size_g": log.serving_size_g,
                    "calories": log.calories,
                    "protein_g": log.protein_g,
                    "carbs_g": log.carbs_g,
                    "fat_g": log.fat_g,
                    "notes": log.notes
                })
            
            # Determine output file path
            if output is None:
                # Default to user's documents folder
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                documents_path = os.path.join(os.path.expanduser("~"), "Documents")
                filename = f"calorie_tracker_{username}_{timestamp}.{format}"
                output = os.path.join(documents_path, filename)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(output)), exist_ok=True)
            
            # Export the data in the specified format
            if format == "csv":
                import csv
                
                with open(output, 'w', newline='') as csvfile:
                    # Define fieldnames
                    fieldnames = [
                        "date", "time", "meal_type", "food_name", "food_brand", 
                        "serving_size_g", "calories", "protein_g", "carbs_g", 
                        "fat_g", "notes"
                    ]
                    
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for entry in export_data:
                        writer.writerow(entry)
                
                click.echo(f"Exported {len(export_data)} food logs to CSV: {output}")
                
            elif format == "json":
                import json
                
                with open(output, 'w') as jsonfile:
                    json_data = {
                        "user": username,
                        "export_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "period_days": days,
                        "logs": export_data
                    }
                    json.dump(json_data, jsonfile, indent=4)
                
                click.echo(f"Exported {len(export_data)} food logs to JSON: {output}")
    
    except Exception as e:
        click.echo(f"Error exporting logs: {e}", err=True)


@export.command("report")
@click.option("--username", prompt=True, help="Username to generate report for")
@click.option("--days", type=int, default=30, help="Number of days to include in report")
@click.option("--output", type=click.Path(), help="Output file path")
@click.option("--include-charts", is_flag=True, default=True, help="Include charts in the report")
def export_report(username, days, output, include_charts):
    """Generate a comprehensive progress report."""
    try:
        # Verify matplotlib is available if charts are requested
        if include_charts:
            try:
                import matplotlib.pyplot as plt
                import matplotlib.dates as mdates
                from matplotlib.figure import Figure
                from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
                import numpy as np
                import pandas as pd
                from io import BytesIO
                import base64
            except ImportError:
                click.echo("Warning: matplotlib not available, charts will be skipped", err=True)
                include_charts = False
        
        with get_db_session() as session:
            # Verify user exists
            user = session.query(User).filter(User.username == username).first()
            if not user:
                click.echo(f"User '{username}' not found", err=True)
                return
            
            # Calculate date range
            end_date = datetime.now()
            start_date = datetime(end_date.year, end_date.month, end_date.day) - timedelta(days=days-1)
            food_logs = (
                session.query(FoodLog)
                .filter(FoodLog.user_id == user.id)
                .filter(FoodLog.log_date >= start_date)
                .filter(FoodLog.log_date <= end_date)
                .join(Food)
                .order_by(FoodLog.log_date)
                .all()
            )
            
            # Query weight logs
            weight_logs = (
                session.query(WeightLog)
                .filter(WeightLog.user_id == user.id)
                .filter(WeightLog.log_date >= start_date)
                .filter(WeightLog.log_date <= end_date)
                .order_by(WeightLog.log_date)
                .all()
            )
            
            # Determine output file path
            if output is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                documents_path = os.path.join(os.path.expanduser("~"), "Documents")
                output = os.path.join(documents_path, f"calorie_tracker_report_{username}_{timestamp}.html")
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(output)), exist_ok=True)
            
            # Prepare data for the report
            # Group logs by date
            logs_by_date = {}
            date_range = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") 
                          for i in range(days)]
            
            for log in food_logs:
                date_key = log.log_date.strftime("%Y-%m-%d")
                if date_key not in logs_by_date:
                    logs_by_date[date_key] = []
                logs_by_date[date_key].append(log)
            
            # Calculate daily totals
            daily_data = []
            
            for date_str in date_range:
                day_logs = logs_by_date.get(date_str, [])
                
                calories = sum(log.calories for log in day_logs)
                protein = sum(log.protein_g for log in day_logs)
                carbs = sum(log.carbs_g for log in day_logs)
                fat = sum(log.fat_g for log in day_logs)
                
                # Calculate percentage of daily goal
                goal_percent = 0
                if user.daily_calorie_goal and calories > 0:
                    goal_percent = (calories / user.daily_calorie_goal) * 100
                
                daily_data.append({
                    "date": date_str,
                    "calories": calories,
                    "protein": protein,
                    "carbs": carbs,
                    "fat": fat,
                    "goal_percent": goal_percent,
                    "log_count": len(day_logs)
                })
            
            # Prepare weight data
            weight_data = [{"date": log.log_date.strftime("%Y-%m-%d"), "weight": log.weight_kg} 
                           for log in weight_logs]
            
            # Generate charts if requested
            chart_data = {}
            if include_charts:
                try:
                    # Convert data to pandas for easier plotting
                    df_food = pd.DataFrame(daily_data)
                    df_food['date'] = pd.to_datetime(df_food['date'])
                    
                    # Only include days with logs for trend visualization
                    df_food_with_logs = df_food[df_food['log_count'] > 0].copy()
                    
                    if not df_food_with_logs.empty:
                        # 1. Calorie intake chart
                        fig_calories = Figure(figsize=(10, 5))
                        ax_calories = fig_calories.add_subplot(111)
                        
                        ax_calories.plot(df_food_with_logs['date'], df_food_with_logs['calories'], 
                                        marker='o', linestyle='-', color='#1f77b4')
                        
                        # Add goal line if available
                        if user.daily_calorie_goal:
                            ax_calories.axhline(y=user.daily_calorie_goal, color='r', linestyle='--', 
                                              alpha=0.7, label=f'Goal: {user.daily_calorie_goal} cal')
                            ax_calories.legend()
                        
                        ax_calories.set_title('Daily Calorie Intake')
                        ax_calories.set_ylabel('Calories')
                        ax_calories.set_xlabel('Date')
                        ax_calories.grid(True, alpha=0.3)
                        
                        # Format x-axis to show dates nicely
                        ax_calories.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                        fig_calories.autofmt_xdate()
                        
                        # Save to BytesIO
                        buf_calories = BytesIO()
                        FigureCanvas(fig_calories).print_png(buf_calories)
                        buf_calories.seek(0)
                        chart_data['calories_chart'] = base64.b64encode(buf_calories.read()).decode('utf-8')
                        
                        # 2. Macronutrient breakdown chart
                        # Calculate average macros for days with logs
                        avg_protein = df_food_with_logs['protein'].mean()
                        avg_carbs = df_food_with_logs['carbs'].mean()
                        avg_fat = df_food_with_logs['fat'].mean()
                        
                        # Convert to calories
                        protein_cal = avg_protein * 4  # 4 calories per gram
                        carbs_cal = avg_carbs * 4      # 4 calories per gram
                        fat_cal = avg_fat * 9          # 9 calories per gram
                        
                        fig_macros = Figure(figsize=(8, 8))
                        ax_macros = fig_macros.add_subplot(111)
                        
                        # Create pie chart
                        labels = ['Protein', 'Carbs', 'Fat']
                        sizes = [protein_cal, carbs_cal, fat_cal]
                        explode = (0.1, 0, 0)  # explode the protein slice
                        
                        ax_macros.pie(sizes, explode=explode, labels=labels, autopct='%1.1f%%',
                                    shadow=True, startangle=140, colors=['#ff9999','#66b3ff','#99ff99'])
                        ax_macros.axis('equal')  # Equal aspect ratio ensures the pie chart is circular
                        ax_macros.set_title('Average Macronutrient Distribution (Calories)')
                        
                        # Save to BytesIO
                        buf_macros = BytesIO()
                        FigureCanvas(fig_macros).print_png(buf_macros)
                        buf_macros.seek(0)
                        chart_data['macros_chart'] = base64.b64encode(buf_macros.read()).decode('utf-8')
                    
                    # 3. Weight trend chart if weight data available
                    if weight_data:
                        df_weight = pd.DataFrame(weight_data)
                        df_weight['date'] = pd.to_datetime(df_weight['date'])
                        
                        fig_weight = Figure(figsize=(10, 5))
                        ax_weight = fig_weight.add_subplot(111)
                        
                        ax_weight.plot(df_weight['date'], df_weight['weight'], 
                                    marker='o', linestyle='-', color='#2ca02c')
                        
                        # Add target weight line if available
                        if user.target_weight_kg:
                            ax_weight.axhline(y=user.target_weight_kg, color='r', linestyle='--', 
                                            alpha=0.7, label=f'Target: {user.target_weight_kg} kg')
                            ax_weight.legend()
                        
                        ax_weight.set_title('Weight Progression')
                        ax_weight.set_ylabel('Weight (kg)')
                        ax_weight.set_xlabel('Date')
                        ax_weight.grid(True, alpha=0.3)
                        
                        # Format x-axis to show dates nicely
                        ax_weight.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                        fig_weight.autofmt_xdate()
                        
                        # Save to BytesIO
                        buf_weight = BytesIO()
                        FigureCanvas(fig_weight).print_png(buf_weight)
                        buf_weight.seek(0)
                        chart_data['weight_chart'] = base64.b64encode(buf_weight.read()).decode('utf-8')
                except Exception as e:
                    click.echo(f"Error generating charts: {e}", err=True)

            # Create HTML report
            try:
                # Calculate summary statistics for the report
                days_with_logs = sum(1 for d in daily_data if d["log_count"] > 0)
                if days_with_logs > 0:
                    days_with_data = [d for d in daily_data if d["log_count"] > 0]
                    avg_calories = sum(d["calories"] for d in days_with_data) / days_with_logs
                    avg_protein = sum(d["protein"] for d in days_with_data) / days_with_logs
                    avg_carbs = sum(d["carbs"] for d in days_with_data) / days_with_logs
                    avg_fat = sum(d["fat"] for d in days_with_data) / days_with_logs
                    
                    if user.daily_calorie_goal:
                        avg_goal_percent = (avg_calories / user.daily_calorie_goal) * 100
                    else:
                        avg_goal_percent = 0
                else:
                    avg_calories = avg_protein = avg_carbs = avg_fat = avg_goal_percent = 0
                
                # Calculate weight change if data available
                weight_change_data = None
                if len(weight_logs) >= 2:
                    first_weight = weight_logs[0].weight_kg
                    last_weight = weight_logs[-1].weight_kg
                    weight_change = last_weight - first_weight
                    
                    if abs(weight_change) < 0.1:
                        weight_change_text = "Weight remained stable"
                    elif weight_change > 0:
                        weight_change_text = f"Gained {weight_change:.1f} kg"
                    else:
                        weight_change_text = f"Lost {abs(weight_change):.1f} kg"
                    
                    weight_change_data = {
                        "first_date": weight_logs[0].log_date.strftime("%Y-%m-%d"),
                        "last_date": weight_logs[-1].log_date.strftime("%Y-%m-%d"),
                        "first_weight": first_weight,
                        "last_weight": last_weight,
                        "change": weight_change,
                        "change_text": weight_change_text
                    }
                
                # Create HTML template
                html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Calorie Tracker Report - {username}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 1px solid #eee;
        }}
        h1 {{
            color: #2c3e50;
        }}
        h2 {{
            color: #3498db;
            margin-top: 30px;
            padding-bottom: 10px;
            border-bottom: 1px solid #eee;
        }}
        .summary-stats {{
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background-color: #f9f9f9;
            border-radius: 8px;
            padding: 15px;
            flex: 1;
            min-width: 200px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stat-card h3 {{
            margin-top: 0;
            color: #2c3e50;
            font-size: 16px;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            color: #3498db;
        }}
        .stat-unit {{
            font-size: 14px;
            color: #7f8c8d;
        }}
        .chart-container {{
            margin: 30px 0;
            text-align: center;
        }}
        .chart {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #f2f2f2;
            font-weight: bold;
            color: #2c3e50;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .footer {{
            margin-top: 50px;
            text-align: center;
            color: #7f8c8d;
            font-size: 14px;
            padding-top: 20px;
            border-top: 1px solid #eee;
        }}
        .goal-progress {{
            height: 20px;
            background-color: #ecf0f1;
            border-radius: 10px;
            margin: 10px 0;
            overflow: hidden;
        }}
        .progress-bar {{
            height: 100%;
            background-color: #2ecc71;
            text-align: center;
            line-height: 20px;
            color: white;
            font-size: 12px;
        }}
        .macro-pill {{
            display: inline-block;
            padding: 5px 10px;
            border-radius: 15px;
            margin-right: 10px;
            font-size: 14px;
            font-weight: bold;
        }}
        .protein {{
            background-color: #ff9999;
            color: #fff;
        }}
        .carbs {{
            background-color: #66b3ff;
            color: #fff;
        }}
        .fat {{
            background-color: #99ff99;
            color: #fff;
        }}
        .weight-change {{
            font-size: 20px;
            font-weight: bold;
            padding: 10px;
            border-radius: 4px;
            display: inline-block;
        }}
        .weight-loss {{
            color: #27ae60;
        }}
        .weight-gain {{
            color: #e74c3c;
        }}
        .weight-stable {{
            color: #3498db;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Nutrition & Fitness Report</h1>
        <p>User: <strong>{username}</strong> | Period: Last {days} Days | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    </div>

    <h2>Summary Statistics</h2>
    <div class="summary-stats">
        <div class="stat-card">
            <h3>Average Daily Calories</h3>
            <div class="stat-value">{avg_calories:.0f}</div>
            <div class="stat-unit">calories/day</div>
        </div>
"""

                # Add goal achievement if available
                if user.daily_calorie_goal:
                    progress_color = "#2ecc71"  # Green by default
                    
                    if avg_goal_percent > 110:
                        progress_color = "#e74c3c"  # Red if over by 10%
                    elif avg_goal_percent < 90:
                        progress_color = "#f39c12"  # Orange if under by 10%
                        
                    html_template += f"""
        <div class="stat-card">
            <h3>Daily Calorie Goal</h3>
            <div class="stat-value">{user.daily_calorie_goal}</div>
            <div class="stat-unit">calories/day</div>
            <div class="goal-progress">
                <div class="progress-bar" style="width: {min(avg_goal_percent, 100):.1f}%; background-color: {progress_color}">
                    {avg_goal_percent:.1f}%
                </div>
            </div>
        </div>"""

                # Add macronutrient stats
                html_template += f"""
        <div class="stat-card">
            <h3>Average Macronutrients</h3>
            <div>
                <span class="macro-pill protein">P: {avg_protein:.1f}g</span>
                <span class="macro-pill carbs">C: {avg_carbs:.1f}g</span>
                <span class="macro-pill fat">F: {avg_fat:.1f}g</span>
            </div>
            <div class="stat-unit">daily average</div>
        </div>
"""

                # Add tracking stats
                html_template += f"""
        <div class="stat-card">
            <h3>Tracking Consistency</h3>
            <div class="stat-value">{days_with_logs}/{days}</div>
            <div class="stat-unit">days tracked</div>
        </div>
    </div>
"""

                # Add weight change information if available
                if weight_change_data:
                    change_class = "weight-stable" if abs(weight_change_data["change"]) < 0.1 else \
                                  "weight-loss" if weight_change_data["change"] < 0 else "weight-gain"
                    
                    html_template += f"""
    <h2>Weight Progress</h2>
    <div class="summary-stats">
        <div class="stat-card">
            <h3>Starting Weight</h3>
            <div class="stat-value">{weight_change_data["first_weight"]:.1f}</div>
            <div class="stat-unit">kg on {weight_change_data["first_date"]}</div>
        </div>
        <div class="stat-card">
            <h3>Current Weight</h3>
            <div class="stat-value">{weight_change_data["last_weight"]:.1f}</div>
            <div class="stat-unit">kg on {weight_change_data["last_date"]}</div>
        </div>
        <div class="stat-card">
            <h3>Change</h3>
            <div class="weight-change {change_class}">{weight_change_data["change_text"]}</div>
        </div>
    </div>
"""

                # Add charts if they were generated
                if chart_data:
                    html_template += """
    <h2>Nutrition Insights</h2>
"""
                    
                    if 'calories_chart' in chart_data:
                        html_template += f"""
    <div class="chart-container">
        <h3>Daily Calorie Intake</h3>
        <img class="chart" src="data:image/png;base64,{chart_data['calories_chart']}" alt="Daily Calorie Intake Chart">
    </div>
"""

                    if 'macros_chart' in chart_data:
                        html_template += f"""
    <div class="chart-container">
        <h3>Macronutrient Distribution</h3>
        <img class="chart" src="data:image/png;base64,{chart_data['macros_chart']}" alt="Macronutrient Distribution Chart">
    </div>
"""

                    if 'weight_chart' in chart_data:
                        html_template += f"""
    <div class="chart-container">
        <h3>Weight Progression</h3>
        <img class="chart" src="data:image/png;base64,{chart_data['weight_chart']}" alt="Weight Progression Chart">
    </div>
"""

                # Add detailed data table
                if days_with_logs > 0:
                    html_template += """
    <h2>Daily Nutrition Data</h2>
    <table>
        <thead>
            <tr>
                <th>Date</th>
                <th>Calories</th>
                <th>Protein (g)</th>
                <th>Carbs (g)</th>
                <th>Fat (g)</th>
                <th>Goal %</th>
                <th>Entries</th>
            </tr>
        </thead>
        <tbody>
"""
                    
                    # Only show days with logs
                    days_with_data = [d for d in daily_data if d["log_count"] > 0]
                    
                    # Sort by date (newest first)
                    for day in sorted(days_with_data, key=lambda x: x["date"], reverse=True):
                        goal_color = ""
                        
                        if user.daily_calorie_goal:
                            if day["goal_percent"] > 110:
                                goal_color = 'style="color: #e74c3c; font-weight: bold;"'  # Red for over
                            elif day["goal_percent"] < 90:
                                goal_color = 'style="color: #f39c12; font-weight: bold;"'  # Orange for under
                            else:
                                goal_color = 'style="color: #27ae60; font-weight: bold;"'  # Green for on target
                        
                        html_template += f"""
            <tr>
                <td>{day['date']}</td>
                <td>{day['calories']}</td>
                <td>{day['protein']:.1f}</td>
                <td>{day['carbs']:.1f}</td>
                <td>{day['fat']:.1f}</td>
                <td {goal_color}>{day['goal_percent']:.1f}%</td>
                <td>{day['log_count']}</td>
            </tr>"""
                        
                    html_template += """
        </tbody>
    </table>
"""

                # Add recommendations section based on data
                html_template += """
    <h2>Recommendations</h2>
"""
                
                # Calorie recommendations
                if user.daily_calorie_goal:
                    if avg_goal_percent > 110:
                        html_template += """
    <p>You're consistently consuming <strong>more calories</strong> than your goal. Consider:</p>
    <ul>
        <li>Reducing portion sizes</li>
        <li>Choosing lower-calorie alternatives</li>
        <li>Increasing physical activity</li>
    </ul>
"""
                    elif avg_goal_percent < 90:
                        html_template += """
    <p>You're consistently consuming <strong>fewer calories</strong> than your goal. Consider:</p>
    <ul>
        <li>Increasing portion sizes of healthy foods</li>
        <li>Adding nutrient-dense snacks between meals</li>
        <li>Including more calorie-dense but nutritious foods</li>
    </ul>
"""
                    else:
                        html_template += """
    <p>You're doing a great job meeting your calorie goals! Keep up the good work and continue your consistent tracking.</p>
"""
                
                # Macronutrient recommendations
                if days_with_logs > 0:
                    # Calculate protein per kg of body weight
                    if user.weight_kg and avg_protein > 0:
                        protein_per_kg = avg_protein / user.weight_kg
                        
                        if protein_per_kg < 0.8:
                            html_template += """
    <p>Your protein intake appears to be <strong>lower than recommended</strong>. Consider:</p>
    <ul>
        <li>Including more lean protein sources like chicken, fish, tofu, or legumes</li>
        <li>Adding protein-rich snacks throughout the day</li>
        <li>Considering a protein supplement if whole food sources are difficult to consume</li>
    </ul>
"""
                            
                    # Check for macro balance
                    if avg_calories > 0:
                        # Calculate macro percentages
                        protein_pct = (avg_protein * 4 / avg_calories) * 100
                        carbs_pct = (avg_carbs * 4 / avg_calories) * 100
                        fat_pct = (avg_fat * 9 / avg_calories) * 100
                        
                        if fat_pct > 40:
                            html_template += """
    <p>Your fat intake is relatively high. While healthy fats are important, consider balancing your diet with more protein and complex carbohydrates.</p>
"""
                        elif carbs_pct > 60:
                            html_template += """
    <p>Your carbohydrate intake is relatively high. Consider focusing on complex carbohydrates and increasing protein intake for better balance.</p>
"""
                
                # Add tracking consistency recommendations
                if days_with_logs < days * 0.7:  # Less than 70% of days tracked
                    html_template += """
    <p>Your tracking consistency could be improved:</p>
    <ul>
        <li>Set a daily reminder to log your meals</li>
        <li>Try to log meals immediately after eating</li>
        <li>Use the app regularly to build a habit</li>
    </ul>
"""
                
                # Close the HTML document
                html_template += """
    <div class="footer">
        <p>Generated by Calorie Tracker Application</p>
    </div>
</body>
</html>
"""
                
                # Write the HTML file
                with open(output, 'w') as html_file:
                    html_file.write(html_template)
                
                click.echo(f"Report successfully generated: {output}")
                
                # Open the report automatically if on a desktop system
                if os.name == 'nt':  # Windows
                    try:
                        import webbrowser
                        webbrowser.open(output)
                    except:
                        pass
                
            except Exception as e:
                click.echo(f"Error generating HTML report: {e}", err=True)
    
    except Exception as e:
        click.echo(f"Error exporting report: {e}", err=True)


# Weight tracking commands
@cli.group()
def weight():
    """Weight tracking commands."""
    pass


@weight.command("log")
@click.option("--username", prompt=True, help="Username to log weight for")
@click.option("--weight-kg", type=float, prompt=True, help="Weight in kilograms")
@click.option("--date", type=click.DateTime(formats=["%Y-%m-%d"]), 
              default=lambda: datetime.now().strftime("%Y-%m-%d"),
              help="Date of the weight measurement (YYYY-MM-DD), defaults to today")
@click.option("--notes", help="Additional notes for this weight entry")
def log_weight(username, weight_kg, date, notes):
    """Log a weight measurement for tracking progress."""
    try:
        with get_db_session() as session:
            # Verify user exists
            user = session.query(User).filter(User.username == username).first()
            if not user:
                click.echo(f"User '{username}' not found", err=True)
                return
            
            # Create weight log entry
            weight_log = WeightLog(
                user_id=user.id,
                weight_kg=weight_kg,
                log_date=date,
                notes=notes
            )
            
            # Add to database
            session.add(weight_log)
            
            # Update user's current weight
            user.weight_kg = weight_kg
            user.updated_at = datetime.utcnow()
            
            session.commit()
            
            click.echo(f"Weight ({weight_kg} kg) logged successfully for {username}")
            
            # Show difference from previous weight if available
            previous_logs = (
                session.query(WeightLog)
                .filter(WeightLog.user_id == user.id)
                .filter(WeightLog.log_date < date)
                .order_by(WeightLog.log_date.desc())
                .first()
            )
            
            if previous_logs:
                diff = weight_kg - previous_logs.weight_kg
                if abs(diff) < 0.01:
                    click.echo("No change from previous measurement.")
                elif diff > 0:
                    click.echo(f"Gained {diff:.1f} kg since previous measurement on {previous_logs.log_date.strftime('%Y-%m-%d')}.")
                else:
                    click.echo(f"Lost {abs(diff):.1f} kg since previous measurement on {previous_logs.log_date.strftime('%Y-%m-%d')}.")
            
            # Check progress toward target if set
            if user.target_weight_kg:
                diff_to_target = weight_kg - user.target_weight_kg
                
                if abs(diff_to_target) < 0.5:
                    click.echo("Congratulations! You've reached your target weight!")
                else:
                    click.echo(f"{abs(diff_to_target):.1f} kg {'above' if diff_to_target > 0 else 'below'} your target weight ({user.target_weight_kg} kg).")
    
    except Exception as e:
        click.echo(f"Error logging weight: {e}", err=True)


@weight.command("history")
@click.option("--username", prompt=True, help="Username to view weight history for")
@click.option("--limit", type=int, default=10, help="Number of entries to show")
@click.option("--show-graph", is_flag=True, help="Show a graph of weight history")
def weight_history(username, limit, show_graph):
    """Show weight history for a user."""
    try:
        with get_db_session() as session:
            # Verify user exists
            user = session.query(User).filter(User.username == username).first()
            if not user:
                click.echo(f"User '{username}' not found", err=True)
                return
            
            # Get weight logs
            weight_logs = (
                session.query(WeightLog)
                .filter(WeightLog.user_id == user.id)
                .order_by(WeightLog.log_date.desc())
                .limit(limit)
                .all()
            )
            
            if not weight_logs:
                click.echo(f"No weight logs found for {username}")
                return
            
            click.echo(f"\nWeight History for {username}:")
            click.echo("-" * 60)
            click.echo(f"{'Date':<12} | {'Weight (kg)':<10} | {'Change':<10} | Notes")
            click.echo("-" * 60)
            
            prev_weight = None
            for i, log in enumerate(weight_logs):
                date_str = log.log_date.strftime("%Y-%m-%d")
                
                # Calculate change from previous entry
                change_str = ""
                if i < len(weight_logs) - 1:  # Not the oldest entry
                    next_log = weight_logs[i+1]  # Previous chronologically (since we're in desc order)
                    change = log.weight_kg - next_log.weight_kg
                    if abs(change) < 0.01:
                        change_str = "no change"
                    elif change > 0:
                        change_str = f"+{change:.1f} kg"
                    else:
                        change_str = f"{change:.1f} kg"
                
                # Format notes or use empty string
                notes_str = log.notes or ""
                
                click.echo(f"{date_str:<12} | {log.weight_kg:<10.1f} | {change_str:<10} | {notes_str}")
            
            click.echo("-" * 60)
            
            # Calculate overall change
            if len(weight_logs) >= 2:
                first = weight_logs[-1]  # Oldest in the list
                last = weight_logs[0]    # Most recent in the list
                total_change = last.weight_kg - first.weight_kg
                
                if abs(total_change) < 0.01:
                    click.echo(f"No change in weight over this period.")
                elif total_change > 0:
                    click.echo(f"Overall gain: {total_change:.1f} kg over this period.")
                else:
                    click.echo(f"Overall loss: {abs(total_change):.1f} kg over this period.")
            
            # Display graph if requested
            if show_graph:
                try:
                    import matplotlib.pyplot as plt
                    import matplotlib.dates as mdates
                    import pandas as pd
                    from datetime import timedelta
                    
                    # Get more historical data for the graph (up to 30 entries)
                    extended_logs = (
                        session.query(WeightLog)
                        .filter(WeightLog.user_id == user.id)
                        .order_by(WeightLog.log_date)  # Ascending for graphing
                        .limit(30)
                        .all()
                    )
                    
                    if extended_logs:
                        # Convert to pandas DataFrame for easier plotting
                        data = {
                            'date': [log.log_date for log in extended_logs],
                            'weight': [log.weight_kg for log in extended_logs]
                        }
                        df = pd.DataFrame(data)
                        
                        # Create the plot
                        plt.figure(figsize=(10, 6))
                        
                        # Plot weight data with connected line and markers
                        plt.plot(df['date'], df['weight'], marker='o', linestyle='-', color='#3498db', 
                                markersize=8, linewidth=2)
                        
                        # Add target weight line if available
                        if user.target_weight_kg:
                            plt.axhline(y=user.target_weight_kg, color='r', linestyle='--', 
                                     alpha=0.7, label=f'Target: {user.target_weight_kg} kg')
                            plt.legend()
                        
                        # Calculate suitable y-axis range
                        min_weight = min(df['weight'])
                        max_weight = max(df['weight'])
                        buffer = max(0.5, (max_weight - min_weight) * 0.2)  # At least 0.5kg or 20% of range
                        
                        # Set plot limits and labels
                        plt.ylim(min_weight - buffer, max_weight + buffer)
                        plt.xlabel('Date')
                        plt.ylabel('Weight (kg)')
                        plt.title(f'Weight History for {username}')
                        plt.grid(True, alpha=0.3)
                        
                        # Format x-axis dates nicely
                        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                        plt.gcf().autofmt_xdate()
                        
                        # Add annotations for key points
                        if len(extended_logs) >= 2:
                            # Annotate first point
                            first_entry = extended_logs[0]
                            plt.annotate(f"{first_entry.weight_kg:.1f} kg", 
                                       xy=(first_entry.log_date, first_entry.weight_kg),
                                       xytext=(-20, -15),
                                       textcoords="offset points",
                                       arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=.2"))
                            
                            # Annotate last point
                            last_entry = extended_logs[-1]
                            plt.annotate(f"{last_entry.weight_kg:.1f} kg", 
                                       xy=(last_entry.log_date, last_entry.weight_kg),
                                       xytext=(10, 10),
                                       textcoords="offset points",
                                       arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=.2"))
                            
                            # Annotate any significant peaks or valleys
                            if len(extended_logs) >= 3:
                                weights = [log.weight_kg for log in extended_logs]
                                max_weight_idx = weights.index(max(weights))
                                min_weight_idx = weights.index(min(weights))
                                
                                # Only annotate if they're not the first or last points
                                if max_weight_idx not in [0, len(extended_logs)-1]:
                                    max_entry = extended_logs[max_weight_idx]
                                    plt.annotate(f"{max_entry.weight_kg:.1f} kg", 
                                               xy=(max_entry.log_date, max_entry.weight_kg),
                                               xytext=(0, 15),
                                               textcoords="offset points",
                                               arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=.2"))
                                
                                if min_weight_idx not in [0, len(extended_logs)-1] and min_weight_idx != max_weight_idx:
                                    min_entry = extended_logs[min_weight_idx]
                                    plt.annotate(f"{min_entry.weight_kg:.1f} kg", 
                                               xy=(min_entry.log_date, min_entry.weight_kg),
                                               xytext=(0, -15),
                                               textcoords="offset points",
                                               arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=.2"))
                        
                        # Show the plot
                        plt.tight_layout()
                        plt.show()
                    
                except ImportError:
                    click.echo("Error: matplotlib is required for graph visualization. Install with 'pip install matplotlib'", err=True)
                except Exception as e:
                    click.echo(f"Error generating weight graph: {e}", err=True)
    
    except Exception as e:
        click.echo(f"Error displaying weight history: {e}", err=True)


# Entry point for CLI
if __name__ == "__main__":
    cli()
