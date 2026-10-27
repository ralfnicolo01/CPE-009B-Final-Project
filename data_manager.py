"""All CSV reading/writing and business rules live here (no UI code)."""
import csv
import json
import uuid
from datetime import date, datetime, timedelta

import config as cfg

FIELDS = {
    cfg.USERS_CSV: ["username", "password", "role"],
    cfg.UNITS_CSV: ["id", "location", "modality", "capacity", "family_name", "headcount", "col", "row"],
    cfg.STOCK_CSV: ["key", "qty", "max"],
    cfg.MEALS_CSV: ["unit_id", "date", "meal", "status", "ration", "qty", "member_id"],
    cfg.DSWD_CSV: ["unit_id", "received_date", "family_id"],
    cfg.LOGS_CSV: ["timestamp", "date", "unit_id", "action", "details"],
    cfg.SETTINGS_CSV: ["key", "value"],
}
INT_FIELDS = ("capacity", "headcount", "col", "row")
_cache = {}   # path -> ((mtime, size), rows): avoids re-parsing a CSV that has not changed


def today() -> str:
    return date.today().isoformat()


def _active(received_date, cycle) -> bool:
    """True while a DSWD pack received on `received_date` is still inside its resupply cycle."""
    return bool(received_date) and (date.today() - date.fromisoformat(received_date)).days < cycle


def _meal(r):
    return ({"status": r["status"], "ration": r["ration"], "qty": int(r["qty"])} if r
            else {"status": "Pending", "ration": "FFP", "qty": 0})


def _read(path):
    if not path.exists():
        return []
    s = path.stat()
    key = (s.st_mtime_ns, s.st_size)
    if _cache.get(path, (None,))[0] != key:
        with open(path, newline="", encoding="utf-8") as f:
            _cache[path] = (key, list(csv.DictReader(f)))
    return [dict(r) for r in _cache[path][1]]


def _write(path, rows):
    _cache.pop(path, None)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS[path], extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)


class DataManager:
    def __init__(self):
        cfg.DATA_DIR.mkdir(exist_ok=True)
        self._init_files()
        self._migrate_users()
        self._migrate_positions()
        self.daily_reset()

    # ---------- setup ----------
    def _init_files(self):
        user, pw = cfg.DEFAULT_ADMIN
        defaults = {
            cfg.USERS_CSV: [{"username": user, "password": pw, "role": cfg.ROLES[0]}],
            cfg.STOCK_CSV: [{"key": k, "qty": q, "max": m} for k, (q, m) in cfg.DEFAULT_STOCK.items()],
            cfg.SETTINGS_CSV: [{"key": "dswd_cycle_days", "value": cfg.DEFAULT_DSWD_CYCLE_DAYS}],
        }
        for path in FIELDS:
            if not path.exists():
                _write(path, defaults.get(path, []))

    # ---------- auth ----------
    def verify_login(self, username, password) -> bool:
        return any(r["username"] == username and r["password"] == password for r in _read(cfg.USERS_CSV))

    def _migrate_users(self):
        """Upgrade older users.csv files: missing roles become Administrator, and accounts that only
        have a hashed password get a plain one (admin -> default, others -> DEFAULT_PASSWORD)."""
        rows = _read(cfg.USERS_CSV)
        if any(not r.get("role") or "password" not in r for r in rows):
            for r in rows:
                r["role"] = r.get("role") or cfg.ROLES[0]
                r.setdefault("password", cfg.DEFAULT_ADMIN[1] if r["username"] == cfg.DEFAULT_ADMIN[0]
                             else cfg.DEFAULT_PASSWORD)
            _write(cfg.USERS_CSV, rows)

    def users(self):
        return [{"username": r["username"], "role": r.get("role") or cfg.ROLES[0]} for r in _read(cfg.USERS_CSV)]

    def role_of(self, username):
        return next((u["role"] for u in self.users() if u["username"] == username), cfg.ROLES[0])

    def _last_admin(self, rows, username):
        """True if `username` is the only Administrator left."""
        admins = [r["username"] for r in rows if r["role"] == cfg.ROLES[0]]
        return admins == [username]

    def add_user(self, username, password, role):
        """Returns (ok, message)."""
        username, rows = username.strip(), _read(cfg.USERS_CSV)
        if not username:
            return False, "Enter a username."
        if any(r["username"].lower() == username.lower() for r in rows):
            return False, "That username is already taken."
        if len(password) < 6:
            return False, "Password must be at least 6 characters."
        if role not in cfg.ROLES:
            return False, "Pick a role."
        rows.append({"username": username, "password": password, "role": role})
        _write(cfg.USERS_CSV, rows)
        self.log("SYSTEM", "User added", f"{username} ({role})")
        return True, ""

    def set_role(self, username, role):
        rows = _read(cfg.USERS_CSV)
        u = next((r for r in rows if r["username"] == username), None)
        if not u or u["role"] == role:
            return True, ""
        if self._last_admin(rows, username):
            return False, "At least one Administrator is required."
        self.log("SYSTEM", "User role changed", f"{username}: {u['role']} -> {role}")
        u["role"] = role
        _write(cfg.USERS_CSV, rows)
        return True, ""

    def delete_user(self, username):
        rows = _read(cfg.USERS_CSV)
        if self._last_admin(rows, username):
            return False, "At least one Administrator is required."
        _write(cfg.USERS_CSV, [r for r in rows if r["username"] != username])
        self.log("SYSTEM", "User deleted", username)
        return True, ""

    # ---------- settings ----------
    def _settings(self):
        return {r["key"]: r["value"] for r in _read(cfg.SETTINGS_CSV)}

    def _put_setting(self, key, value):
        s = self._settings()
        s[key] = value
        _write(cfg.SETTINGS_CSV, [{"key": k, "value": v} for k, v in s.items()])

    def _int_setting(self, key, default):
        try:
            return int(self._settings().get(key, default))
        except ValueError:
            return default

    def cycle_days(self) -> int:
        return self._int_setting("dswd_cycle_days", cfg.DEFAULT_DSWD_CYCLE_DAYS)

    def set_cycle(self, days):
        old = self.cycle_days()
        self._put_setting("dswd_cycle_days", days)
        if old != days:
            self.log("SYSTEM", "Setting changed", f"DSWD cycle: {old} -> {days} days")

    def dark(self) -> bool:
        return self._int_setting("dark_mode", 0) == 1

    def set_dark(self, on):
        self._put_setting("dark_mode", int(on))

    def grid_size(self):
        """(columns, rows) of the shelter layout grid."""
        return (self._int_setting("grid_cols", cfg.DEFAULT_GRID[0]),
                self._int_setting("grid_rows", cfg.DEFAULT_GRID[1]))

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
        miss = lambda r: r.get("col", "") == "" or r.get("row", "") == ""
        todo = [r for r in rows if miss(r)]
        if not todo:
            return
        cols, grid_rows = self.grid_size()
        taken = {(int(r["col"]), int(r["row"])) for r in rows if not miss(r)}
        n = 0
        for r in todo:
            while (n % cols, n // cols) in taken:
                n += 1
            r["col"], r["row"] = n % cols, n // cols
            taken.add((r["col"], r["row"]))
        need = max(int(r["row"]) for r in rows) + 1
        if need > grid_rows:
            self._put_setting("grid_rows", need)
        _write(cfg.UNITS_CSV, rows)

    def units(self):
        result = []
        for raw in _read(cfg.UNITS_CSV):
            u = {**raw, **{k: int(raw[k]) for k in INT_FIELDS}}
            try:
                families = json.loads(raw.get("family_name", ""))
            except (TypeError, json.JSONDecodeError):
                families = None  # added: distinguish legacy text from a parsed family list
            if isinstance(families, list):
                u["families"] = families
                u["family_name"] = ", ".join(f.get("family_name", "") for f in families)
            else:
                u["families"] = []
            result.append(u)
        return result

    def families(self, uid):
        raw = next((r for r in _read(cfg.UNITS_CSV) if r["id"] == uid), None)
        if not raw:
            return []
        try:
            data = json.loads(raw.get("family_name", ""))
            if isinstance(data, list):
                changed = False
                for family in data:
                    if not family.get("id"):
                        family["id"] = uuid.uuid4().hex[:12]; changed = True
                    if not isinstance(family.get("members"), list):
                        family["members"] = []
                        for i in range(int(family.get("headcount", 0) or 0)):
                            family["members"].append({"name": f"Member {i + 1}", "age": "", "barangay": ""})
                        changed = True
                    for i, member in enumerate(family["members"]):
                        if not member.get("id"):
                            member["id"] = uuid.uuid4().hex[:12]; changed = True
                        member.setdefault("name", member.get("full_name", f"Member {i + 1}"))
                        member.setdefault("age", "")
                        member.setdefault("barangay", "")
                if changed:
                    self.update_unit(uid, {"families": data})
                return data
        except (TypeError, json.JSONDecodeError):
            pass
        # Upgrade legacy family/headcount fields without losing the old occupant count.
        name = raw.get("family_name", "").strip()
        count = int(raw.get("headcount", 0) or 0)
        if not name and not count:
            return []
        family = {"id": uuid.uuid4().hex[:12], "family_name": name or "Legacy family", "members": []}
        for i in range(count):
            family["members"].append({"id": uuid.uuid4().hex[:12], "name": f"Member {i + 1}", "age": "", "barangay": ""})
        self.update_unit(uid, {"families": [family]})
        return [family]

    def add_unit(self, location, modality, capacity, col, row, family_name="", headcount=0) -> str:
        units = _read(cfg.UNITS_CSV)
        prefix = "T" if modality == "Tent" else "C"
        nums = [int(u["id"].split("-")[1]) for u in units if u["id"].startswith(prefix + "-")]
        uid = f"{prefix}-{max(nums, default=0) + 1:03d}"
        units.append({"id": uid, "location": location, "modality": modality, "capacity": capacity,
                      "family_name": family_name, "headcount": headcount, "col": col, "row": row})
        _write(cfg.UNITS_CSV, units)
        self.log(uid, "Unit added", f"{modality} at {location}, capacity {capacity}, "
                                    f"cell column {col + 1} / row {row + 1}")
        return uid

    def update_unit(self, uid, fields):
        """fields: location, family_name, modality, capacity, headcount (any subset)."""
        units = _read(cfg.UNITS_CSV)
        u = next((x for x in units if x["id"] == uid), None)
        if not u:
            return False
        changes = []
        for k, v in fields.items():
            if k == "families":
                names = ", ".join(f.get("family_name", "") for f in v)
                headcount = sum(len(f.get("members", [])) for f in v)
                changes.append(f"families updated ({len(v)} families / {headcount} occupants)")
                u["family_name"] = json.dumps(v, ensure_ascii=False)
                u["headcount"] = headcount
            elif k == "family_name" and "families" in fields:
                # families is the structured source of truth; keep legacy display data out of CSV.
                continue
            elif k in FIELDS[cfg.UNITS_CSV] and u.get(k) != str(v):
                changes.append(f"{k}: {u.get(k, '')} -> {v}")
                u[k] = str(v)
        _write(cfg.UNITS_CSV, units)
        if changes:
            self.log(uid, "Unit edited", "; ".join(changes))
        return True

    def move_unit(self, uid, col, row):
        """Move a unit to a cell; if the cell is taken, the two units swap places."""
        units = _read(cfg.UNITS_CSV)
        me = next((u for u in units if u["id"] == uid), None)
        if not me or (int(me["col"]), int(me["row"])) == (col, row):
            return
        other = next((u for u in units if u["id"] != uid and (int(u["col"]), int(u["row"])) == (col, row)), None)
        if other:
            other["col"], other["row"] = me["col"], me["row"]
        me["col"], me["row"] = str(col), str(row)
        _write(cfg.UNITS_CSV, units)
        self.log(uid, "Unit moved", f"to column {col + 1} / row {row + 1}"
                                    + (f" (swapped with {other['id']})" if other else ""))

    def delete_unit(self, uid):
        _write(cfg.UNITS_CSV, [u for u in _read(cfg.UNITS_CSV) if u["id"] != uid])
        for path in (cfg.MEALS_CSV, cfg.DSWD_CSV):
            _write(path, [r for r in _read(path) if r["unit_id"] != uid])
        self.log(uid, "Unit deleted", "")

    # ---------- stock ----------
    def stock(self):
        rows = {r["key"]: r for r in _read(cfg.STOCK_CSV)}
        return {k: {"label": label, "qty": int(rows[k]["qty"]), "max": int(rows[k]["max"])}
                for k, label in cfg.STOCK_ITEMS.items() if k in rows}

    def _save_stock(self, stock):
        _write(cfg.STOCK_CSV, [{"key": k, "qty": v["qty"], "max": v["max"]} for k, v in stock.items()])

    def set_stock(self, key, qty, mx):
        stock = self.stock()
        o = stock[key]
        if (o["qty"], o["max"]) != (qty, mx):
            self.log("SYSTEM", "Stock edited", f"{o['label']}: {o['qty']}/{o['max']} -> {qty}/{mx}")
            stock[key].update(qty=qty, max=mx)
            self._save_stock(stock)

    # ---------- distribution state ----------
    def today_state(self):
        t, cycle = today(), self.cycle_days()
        meal_rows = [r for r in _read(cfg.MEALS_CSV) if r["date"] == t]
        dswd_rows = _read(cfg.DSWD_CSV)
        state = {}
        for u in self.units():
            uid = u["id"]
            active_member_ids = {m["id"] for f in u["families"] for m in f.get("members", []) if m.get("id")}
            unit_meals = {}
            for m in cfg.MEALS:
                rows = [r for r in meal_rows if r["unit_id"] == uid and r["meal"] == m]
                legacy = next((r for r in rows if not r.get("member_id")), None)
                members = [r for r in rows if r.get("member_id") in active_member_ids]
                if legacy and not members:
                    unit_meals[m] = _meal(legacy)
                else:
                    count = sum(1 for r in members if r["status"] == "Received")
                    ration = members[0]["ration"] if members else "FFP"
                    unit_meals[m] = {"status": "Received" if count > 0 and count == u["headcount"] else "Pending",
                                     "ration": ration, "qty": count}
            # Older saved family JSON has no IDs; UnitDialog upgrades it when opened.
            family_ids = {f.get("id") for f in u["families"] if f.get("id")}  # added: skip older families without IDs
            fam_dswd = [r for r in dswd_rows if r["unit_id"] == uid and r.get("family_id") in family_ids]
            active_dates = [r["received_date"] for r in fam_dswd if _active(r.get("received_date", ""), cycle)]
            legacy = next((r for r in dswd_rows if r["unit_id"] == uid and not r.get("family_id")), None)
            d = max(active_dates, default=legacy["received_date"] if legacy else "")
            state[uid] = {
                "meals": unit_meals,
                "dswd": {"received": _active(d, cycle), "date": d,
                         "next_due": (date.fromisoformat(d) + timedelta(days=cycle)).isoformat() if d else ""}}
        return state

    def set_member_meal(self, uid, member_id, meal, status, ration):
        """Set today's ration for one evacuee, adjusting counted stock by one item."""
        rows = _read(cfg.MEALS_CSV); t = today()
        cur = next((r for r in rows if r.get("member_id") == member_id and r["date"] == t and r["meal"] == meal), None)
        if cur and cur["status"] == status and (status != "Received" or cur["ration"] == ration):
            return True, ""
        stock = self.stock()
        if cur and cur["status"] == "Received" and cur["ration"] in stock:
            stock[cur["ration"]]["qty"] += int(cur["qty"] or 0)
        qty = 1 if status == "Received" else 0
        if qty and ration in stock:
            if stock[ration]["qty"] < 1:
                return False, f"No {stock[ration]['label']} left in stock."
            stock[ration]["qty"] -= 1
        record = {"unit_id": uid, "date": t, "meal": meal, "status": status,
                  "ration": ration, "qty": qty, "member_id": member_id}
        if cur:
            cur.update({k: str(v) for k, v in record.items()})
        else:
            rows.append(record)
        _write(cfg.MEALS_CSV, rows); self._save_stock(stock)
        self.log(uid, "Meal update", f"{meal}: {status} for one member ({cfg.RATIONS[ration]})")
        return True, ""

    def member_meals_today(self, uid, member_id):
        rows = [r for r in _read(cfg.MEALS_CSV) if r.get("unit_id") == uid and r.get("member_id") == member_id and r.get("date") == today()]
        return {m: next((r for r in rows if r["meal"] == m), {"status": "Pending", "ration": "FFP"}) for m in cfg.MEALS}

    def dswd_family_state(self, uid, family_id):
        rows = _read(cfg.DSWD_CSV)
        r = next((x for x in rows if x["unit_id"] == uid and x.get("family_id") == family_id), None)
        if not r and self.families(uid) and self.families(uid)[0]["id"] == family_id:
            r = next((x for x in rows if x["unit_id"] == uid and not x.get("family_id")), None)
        d = r.get("received_date", "") if r else ""
        cycle = self.cycle_days()
        return {"received": _active(d, cycle), "date": d,
                "next_due": (date.fromisoformat(d) + timedelta(days=cycle)).isoformat() if d else ""}

    def set_dswd_family(self, uid, family_id, received):
        rows = _read(cfg.DSWD_CSV)
        cur = next((r for r in rows if r["unit_id"] == uid and r.get("family_id") == family_id), None)
        migrated_legacy = False
        if not cur and self.families(uid) and self.families(uid)[0]["id"] == family_id:
            cur = next((r for r in rows if r["unit_id"] == uid and not r.get("family_id")), None)
            if cur:
                cur["family_id"] = family_id
                migrated_legacy = True
        if received == _active(cur.get("received_date", "") if cur else "", self.cycle_days()):
            if migrated_legacy:
                _write(cfg.DSWD_CSV, rows)
            return True, ""
        stock = self.stock()
        if received and stock["DSWD"]["qty"] < 1:
            return False, "No DSWD relief packs left in stock."
        stock["DSWD"]["qty"] += -1 if received else 1
        if cur:
            cur["received_date"] = today() if received else ""
        else:
            rows.append({"unit_id": uid, "received_date": today() if received else "", "family_id": family_id})
        _write(cfg.DSWD_CSV, rows); self._save_stock(stock)
        self.log(uid, "DSWD family pack", f"{family_id}: " + ("Received" if received else "Reverted"))
        return True, ""

    def set_meal(self, uid, meal, status, ration):
        """Mark a meal Received/Pending for today. Adjusts stock. Returns (ok, message)."""
        t = today()
        rows = _read(cfg.MEALS_CSV)
        cur = next((r for r in rows if (r["unit_id"], r["date"], r["meal"]) == (uid, t, meal)), None)
        if (cur is None and status == "Pending") or \
           (cur and cur["status"] == status and (status != "Received" or cur["ration"] == ration)):
            return True, ""
        unit = next(u for u in self.units() if u["id"] == uid)
        stock = self.stock()
        if cur and cur["status"] == "Received" and cur["ration"] in stock:
            stock[cur["ration"]]["qty"] += int(cur["qty"])
        qty = 0
        if status == "Received":
            qty = unit["headcount"]
            if qty <= 0:
                return False, "No evacuees registered in this unit."
            if ration in stock:                 # FFP / hot meals are not counted
                have = stock[ration]["qty"]
                if have < qty:
                    return False, f"Not enough {stock[ration]['label']} (need {qty}, have {have})."
                stock[ration]["qty"] -= qty
        new = {"unit_id": uid, "date": t, "meal": meal, "status": status, "ration": ration, "qty": qty}
        if cur:
            cur.update({k: str(v) for k, v in new.items()})
        else:
            rows.append(new)
        _write(cfg.MEALS_CSV, rows)
        self._save_stock(stock)
        self.log(uid, "Meal update", f"{meal}: Received - {cfg.RATIONS[ration]} x{qty}" if status == "Received"
                 else f"{meal}: reverted to Pending (stock returned)")
        return True, ""

    def set_dswd(self, uid, received):
        rows = _read(cfg.DSWD_CSV)
        cur = next((r for r in rows if r["unit_id"] == uid), None)
        if received == _active(cur["received_date"] if cur else "", self.cycle_days()):
            return True, ""
        stock = self.stock()
        if received:
            if stock["DSWD"]["qty"] < 1:
                return False, "No DSWD relief packs left in stock."
        stock["DSWD"]["qty"] += -1 if received else 1
        d = today() if received else ""
        if cur:
            cur["received_date"] = d
        else:
            rows.append({"unit_id": uid, "received_date": d})
        _write(cfg.DSWD_CSV, rows)
        self._save_stock(stock)
        self.log(uid, "DSWD pack", "Received" if received else "Reverted to Not received")
        return True, ""

    # ---------- logs ----------
    def log(self, unit_id, action, details=""):
        now = datetime.now()
        _cache.pop(cfg.LOGS_CSV, None)
        with open(cfg.LOGS_CSV, "a", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=FIELDS[cfg.LOGS_CSV]).writerow({
                "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"), "date": now.date().isoformat(),
                "unit_id": unit_id, "action": action, "details": details})

    def log_dates(self):
        return sorted({r["date"] for r in _read(cfg.LOGS_CSV)} | {today()}, reverse=True)

    def logs_for(self, day):
        return [r for r in reversed(_read(cfg.LOGS_CSV)) if r["date"] == day]

    # ---------- daily reset ----------
    def daily_reset(self):
        """Meals reset automatically (records are per-date). Here we log it once a day
        and clear DSWD records whose resupply cycle has ended."""
        if any((r["unit_id"], r["date"], r["action"]) == ("SYSTEM", today(), "Daily reset")
               for r in _read(cfg.LOGS_CSV)):
            return
        cycle = self.cycle_days()
        rows = _read(cfg.DSWD_CSV)
        for r in rows:
            if r["received_date"] and not _active(r["received_date"], cycle):
                self.log(r["unit_id"], "DSWD reset", f"Cycle ended (received {r['received_date']})")
                r["received_date"] = ""
        _write(cfg.DSWD_CSV, rows)
        self.log("SYSTEM", "Daily reset", "Breakfast / Lunch / Dinner distribution status reset")
