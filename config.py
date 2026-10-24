"""Central configuration: file paths and constants."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

USERS_CSV = DATA_DIR / "users.csv"
UNITS_CSV = DATA_DIR / "units.csv"
STOCK_CSV = DATA_DIR / "stock.csv"
MEALS_CSV = DATA_DIR / "meals.csv"
DSWD_CSV = DATA_DIR / "dswd.csv"
LOGS_CSV = DATA_DIR / "logs.csv"
SETTINGS_CSV = DATA_DIR / "settings.csv"

MODALITIES = ("Tent", "Classroom")
MEALS = ("Breakfast", "Lunch", "Dinner")

# Ration types a person can receive for a meal (dropdown in the unit dialog)
RATIONS = {
    "FFP": "1. Family Food Pack (FFP)",
    "RTEF": "2. Ready-to-Eat Food (RTEF)",
    "HOT": "3. Hot Meal (Lomi / Soup / Rice)",
}

# Stock items shown on the dashboard
STOCK_ITEMS = {
    "FFP": "Family Food Packs (FFPs)",
    "RTEF": "Ready-to-Eat Food (RTEF) / Breakfast & Meal Packs",
    "HOT": "Hot Meals (Lomi, Soup, Rice Meals)",
    "DSWD": "DSWD Relief Packs",
}
DEFAULT_STOCK = {"FFP": (500, 500), "RTEF": (500, 500), "HOT": (300, 300), "DSWD": (200, 200)}

DEFAULT_DSWD_CYCLE_DAYS = 3
DEFAULT_GRID = (6, 4)   # columns, rows of the shelter layout grid
DEFAULT_ADMIN = ("admin", "admin123")
