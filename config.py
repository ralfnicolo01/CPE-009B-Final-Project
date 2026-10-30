"""Central configuration: file paths and constants."""
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)   # make sure the data folder exists (important for the built exe)

USERS_CSV, UNITS_CSV, STOCK_CSV, MEALS_CSV, DSWD_CSV, LOGS_CSV, SETTINGS_CSV = (
    DATA_DIR / f"{n}.csv" for n in ("users", "units", "stock", "meals", "dswd", "logs", "settings"))

MODALITIES = ("Tent", "Classroom")
MEALS = ("Breakfast", "Lunch", "Dinner")

# Ration types a person can receive for a meal (dropdown in the unit dialog)
RATIONS = {
    "FFP": "Family Food Pack (FFP)",
    "RTEF": "Ready-to-Eat Food (RTEF)",
    "HOT": "Hot Meal (Lomi / Soup / Rice)",
}

# Counted stock items (FFP and hot meals are still ration choices, but are not tracked in stock)
STOCK_ITEMS = {
    "RTEF": "Ready-to-Eat Food (RTEF) / Breakfast & Meal Packs",
    "DSWD": "DSWD Relief Packs",
}
DEFAULT_STOCK = {"RTEF": (500, 500), "DSWD": (200, 200)}

DEFAULT_DSWD_CYCLE_DAYS = 3
DEFAULT_GRID = (6, 4)   # columns, rows of the shelter layout grid
DEFAULT_ADMIN = ("admin", "admin123")
DEFAULT_PASSWORD = "changeme"   # given to old hashed accounts when upgrading (their real password is unrecoverable)
ROLES = ("Administrator", "DSWD Personnel", "Barangay Assistant", "Teacher", "Health Worker", "Volunteer")
# Only ROLES[0] (Administrator) can open the Users page