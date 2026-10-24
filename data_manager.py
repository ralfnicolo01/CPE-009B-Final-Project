"""All CSV reading/writing and business rules live here (no UI code)."""
import csv
import hashlib
import hmac
import secrets
from datetime import date, datetime, timedelta

import config as cfg

USER_F = ["username", "salt", "hash"]
UNIT_F = ["id", "location", "modality", "capacity", "family_name", "headcount", "col", "row"]
STOCK_F = ["key", "qty", "max"]
MEAL_F = ["unit_id", "date", "meal", "status", "ration", "qty"]
DSWD_F = ["unit_id", "received_date"]
LOG_F = ["timestamp", "date", "unit_id", "action", "details"]
SET_F = ["key", "value"]


def today() -> str:
    return date.today().isoformat()


def _read(path):
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write(path, fields, rows):
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)


def _hash(password, salt):
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


class DataManager:
    def __init__(self):
        cfg.DATA_DIR.mkdir(exist_ok=True)
        self._init_files()
        self._migrate_positions()
        self.daily_reset()

    # ---------- setup ----------
    def _init_files(self):
        if not cfg.USERS_CSV.exists():
            salt = secrets.token_hex(8)
            user, pw = cfg.DEFAULT_ADMIN
            _write(cfg.USERS_CSV, USER_F, [{"username": user, "salt": salt, "hash": _hash(pw, salt)}])
        if not cfg.STOCK_CSV.exists():
            _write(cfg.STOCK_CSV, STOCK_F,
                   [{"key": k, "qty": q, "max": m} for k, (q, m) in cfg.DEFAULT_STOCK.items()])
        if not cfg.SETTINGS_CSV.exists():
            _write(cfg.SETTINGS_CSV, SET_F,
                   [{"key": "dswd_cycle_days", "value": cfg.DEFAULT_DSWD_CYCLE_DAYS}])
        for path, fields in ((cfg.UNITS_CSV, UNIT_F), (cfg.MEALS_CSV, MEAL_F),
                             (cfg.DSWD_CSV, DSWD_F), (cfg.LOGS_CSV, LOG_F)):
            if not path.exists():
                _write(path, fields, [])

    # ---------- auth ----------
    def verify_login(self, username, password) -> bool:
        for r in _read(cfg.USERS_CSV):
            if r["username"] == username:
                return hmac.compare_digest(r["hash"], _hash(password, r["salt"]))
        return False

    # ---------- settings ----------
    def _settings(self):
        return {r["key"]: r["value"] for r in _read(cfg.SETTINGS_CSV)}

    def _put_setting(self, key, value):
        s = self._settings()
        s[key] = value
        _write(cfg.SETTINGS_CSV, SET_F, [{"key": k, "value": v} for k, v in s.items()])

    def cycle_days(self) -> int:
        try:
            return int(self._settings().get("dswd_cycle_days", cfg.DEFAULT_DSWD_CYCLE_DAYS))
        except ValueError:
            return cfg.DEFAULT_DSWD_CYCLE_DAYS

    def set_cycle(self, days):
        old = self.cycle_days()
        self._put_setting("dswd_cycle_days", days)
        if old != days:
            self.log("SYSTEM", "Setting changed", f"DSWD cycle: {old} -> {days} days")

    def grid_size(self):
        """(columns, rows) of the shelter layout grid."""
        s = self._settings()
        try:
            return (int(s.get("grid_cols", cfg.DEFAULT_GRID[0])),
                    int(s.get("grid_rows", cfg.DEFAULT_GRID[1])))
        except ValueError:
            return cfg.DEFAULT_GRID

    def set_grid(self, cols, rows):
        for u in self.units():
            if u["col"] >= cols or u["row"] >= rows:
                return False, (f"{u['id']} sits at column {u['col'] + 1}, row {u['row'] + 1}, "
                               "outside the new size. Move it first.")
        old = self.grid_size()
        self._put_setting("grid_cols", cols)
        self._put_setting("grid_rows", rows)
        if old != (cols, rows):
            self.log("SYSTEM", "Setting changed", f"Grid: {old[0]}x{old[1]} -> {cols}x{rows}")
        return True, ""

    # ---------- units ----------
    def _migrate_positions(self):
        """Give units from older data files a grid cell (first free cell, row by row)."""
        rows = _read(cfg.UNITS_CSV)
        missing = lambda r: r.get("col", "") == "" or r.get("row", "") == ""
        if not any(missing(r) for r in rows):
            return
        cols, grid_rows = self.grid_size()
        taken = {(int(r["col"]), int(r["row"])) for r in rows if not missing(r)}
        n = 0
        for r in rows:
            if missing(r):
                while (n % cols, n // cols) in taken:
                    n += 1
                r["col"], r["row"] = n % cols, n // cols
                taken.add((r["col"], r["row"]))
        need = max(int(r["row"]) for r in rows) + 1
        if need > grid_rows:
            self._put_setting("grid_rows", need)
        _write(cfg.UNITS_CSV, UNIT_F, rows)

    def units(self):
        out = []
        for r in _read(cfg.UNITS_CSV):
            r["capacity"] = int(r["capacity"])
            r["headcount"] = int(r["headcount"])
            r["col"] = int(r["col"])
            r["row"] = int(r["row"])
            out.append(r)
        return out

    def _save_units(self, units):
        _write(cfg.UNITS_CSV, UNIT_F, units)

    def add_unit(self, location, modality, capacity, col, row, family_name="", headcount=0) -> str:
        units = self.units()
        prefix = "T" if modality == "Tent" else "C"
        nums = [int(u["id"].split("-")[1]) for u in units if u["id"].startswith(prefix + "-")]
        uid = f"{prefix}-{max(nums, default=0) + 1:03d}"
        units.append({"id": uid, "location": location, "modality": modality,
                      "capacity": capacity, "family_name": family_name,
                      "headcount": headcount, "col": col, "row": row})
        self._save_units(units)
        self.log(uid, "Unit added", f"{modality} at {location}, capacity {capacity}, "
                                    f"cell column {col + 1} / row {row + 1}")
        return uid

    def update_unit(self, uid, fields):
        """fields: location, family_name, modality, capacity, headcount (any subset)."""
        units = self.units()
        u = next((x for x in units if x["id"] == uid), None)
        if not u:
            return False
        changes = [f"{k}: {u[k]} -> {v}" for k, v in fields.items() if u.get(k) != v]
        u.update(fields)
        self._save_units(units)
        if changes:
            self.log(uid, "Unit edited", "; ".join(changes))
        return True

    def move_unit(self, uid, col, row):
        """Move a unit to a cell; if the cell is taken, the two units swap places."""
        units = self.units()
        me = next((u for u in units if u["id"] == uid), None)
        if not me or (me["col"], me["row"]) == (col, row):
            return
        other = next((u for u in units if u["id"] != uid and u["col"] == col and u["row"] == row), None)
        if other:
            other["col"], other["row"] = me["col"], me["row"]
        me["col"], me["row"] = col, row
        self._save_units(units)
        self.log(uid, "Unit moved", f"to column {col + 1} / row {row + 1}"
                                    + (f" (swapped with {other['id']})" if other else ""))

    def delete_unit(self, uid):
        self._save_units([u for u in self.units() if u["id"] != uid])
        _write(cfg.MEALS_CSV, MEAL_F, [r for r in _read(cfg.MEALS_CSV) if r["unit_id"] != uid])
        _write(cfg.DSWD_CSV, DSWD_F, [r for r in _read(cfg.DSWD_CSV) if r["unit_id"] != uid])
        self.log(uid, "Unit deleted", "")

    # ---------- stock ----------
    def stock(self):
        rows = {r["key"]: r for r in _read(cfg.STOCK_CSV)}
        return {k: {"label": label, "qty": int(rows[k]["qty"]), "max": int(rows[k]["max"])}
                for k, label in cfg.STOCK_ITEMS.items() if k in rows}

    def _save_stock(self, stock):
        _write(cfg.STOCK_CSV, STOCK_F,
               [{"key": k, "qty": v["qty"], "max": v["max"]} for k, v in stock.items()])

    def set_stock(self, key, qty, mx):
        stock = self.stock()
        o = stock[key]
        if o["qty"] != qty or o["max"] != mx:
            self.log("SYSTEM", "Stock edited",
                     f"{o['label']}: {o['qty']}/{o['max']} -> {qty}/{mx}")
            stock[key].update(qty=qty, max=mx)
            self._save_stock(stock)

    # ---------- distribution state ----------
    def today_state(self):
        t = today()
        meals = {(r["unit_id"], r["meal"]): r for r in _read(cfg.MEALS_CSV) if r["date"] == t}
        dswd = {r["unit_id"]: r["received_date"] for r in _read(cfg.DSWD_CSV)}
        cycle = self.cycle_days()
        state = {}
        for u in self.units():
            uid = u["id"]
            m = {}
            for meal in cfg.MEALS:
                r = meals.get((uid, meal))
                m[meal] = {"status": r["status"] if r else "Pending",
                           "ration": r["ration"] if r else "FFP",
                           "qty": int(r["qty"]) if r else 0}
            d = dswd.get(uid, "")
            received, nxt = False, ""
            if d:
                dd = date.fromisoformat(d)
                received = (date.today() - dd).days < cycle
                nxt = (dd + timedelta(days=cycle)).isoformat()
            state[uid] = {"meals": m, "dswd": {"received": received, "date": d, "next_due": nxt}}
        return state

    def set_meal(self, uid, meal, status, ration):
        """Mark a meal Received/Pending for today. Adjusts stock. Returns (ok, message)."""
        t = today()
        rows = _read(cfg.MEALS_CSV)
        cur = next((r for r in rows if r["unit_id"] == uid and r["date"] == t and r["meal"] == meal), None)
        if (cur is None and status == "Pending") or \
           (cur and cur["status"] == status and (status != "Received" or cur["ration"] == ration)):
            return True, ""
        unit = next(u for u in self.units() if u["id"] == uid)
        stock = self.stock()
        if cur and cur["status"] == "Received":
            stock[cur["ration"]]["qty"] += int(cur["qty"])
        qty = 0
        if status == "Received":
            qty = unit["headcount"]
            if qty <= 0:
                return False, "No evacuees registered in this unit."
            have = stock[ration]["qty"]
            if have < qty:
                return False, f"Not enough {stock[ration]['label']} (need {qty}, have {have})."
            stock[ration]["qty"] -= qty
        new = {"unit_id": uid, "date": t, "meal": meal, "status": status, "ration": ration, "qty": qty}
        if cur:
            cur.update({k: str(v) for k, v in new.items()})
        else:
            rows.append(new)
        _write(cfg.MEALS_CSV, MEAL_F, rows)
        self._save_stock(stock)
        detail = (f"{meal}: Received - {cfg.RATIONS[ration]} x{qty}" if status == "Received"
                  else f"{meal}: reverted to Pending (stock returned)")
        self.log(uid, "Meal update", detail)
        return True, ""

    def set_dswd(self, uid, received):
        rows = _read(cfg.DSWD_CSV)
        cur = next((r for r in rows if r["unit_id"] == uid), None)
        cycle = self.cycle_days()
        active = bool(cur and cur["received_date"] and
                      (date.today() - date.fromisoformat(cur["received_date"])).days < cycle)
        if received == active:
            return True, ""
        stock = self.stock()
        if received:
            if stock["DSWD"]["qty"] < 1:
                return False, "No DSWD relief packs left in stock."
            stock["DSWD"]["qty"] -= 1
            d = today()
        else:
            stock["DSWD"]["qty"] += 1
            d = ""
        if cur:
            cur["received_date"] = d
        else:
            rows.append({"unit_id": uid, "received_date": d})
        _write(cfg.DSWD_CSV, DSWD_F, rows)
        self._save_stock(stock)
        self.log(uid, "DSWD pack", "Received" if received else "Reverted to Not received")
        return True, ""

    # ---------- logs ----------
    def log(self, unit_id, action, details=""):
        now = datetime.now()
        with open(cfg.LOGS_CSV, "a", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=LOG_F).writerow({
                "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"), "date": now.date().isoformat(),
                "unit_id": unit_id, "action": action, "details": details})

    def log_dates(self):
        dates = {r["date"] for r in _read(cfg.LOGS_CSV)} | {today()}
        return sorted(dates, reverse=True)

    def logs_for(self, day):
        return [r for r in reversed(_read(cfg.LOGS_CSV)) if r["date"] == day]

    # ---------- daily reset ----------
    def daily_reset(self):
        """Meals reset automatically (records are per-date). Here we log it once a day
        and clear DSWD records whose resupply cycle has ended."""
        t = today()
        if any(r["unit_id"] == "SYSTEM" and r["date"] == t and r["action"] == "Daily reset"
               for r in _read(cfg.LOGS_CSV)):
            return
        cycle = self.cycle_days()
        rows = _read(cfg.DSWD_CSV)
        for r in rows:
            if r["received_date"] and (date.today() - date.fromisoformat(r["received_date"])).days >= cycle:
                self.log(r["unit_id"], "DSWD reset", f"Cycle ended (received {r['received_date']})")
                r["received_date"] = ""
        _write(cfg.DSWD_CSV, DSWD_F, rows)
        self.log("SYSTEM", "Daily reset", "Breakfast / Lunch / Dinner distribution status reset")
