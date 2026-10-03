# -*- coding: utf-8 -*-
import asyncio
import json
import os
import time
import uuid
import hashlib
import random
from datetime import datetime      # 👈 ADD KARO
import pytz                        # 👈 ADD KARO 
from typing import Dict, List, Any, Optional, Tuple
from aiohttp import web

TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html") 

# ==================== TIMEZONE CONFIG (INDIA - IST) ====================
LOCAL_TZ = pytz.timezone("Asia/Kolkata")   # 🇮🇳 Indian Standard Time

def now_local() -> datetime:
    """Current time in IST"""
    return datetime.now(LOCAL_TZ)

def fmt_time() -> str:
    """HH:MM:SS in IST"""
    return now_local().strftime("%H:%M:%S")

def fmt_datetime() -> str:
    """YYYY-MM-DD HH:MM:SS in IST"""
    return now_local().strftime("%Y-%m-%d %H:%M:%S")
# =====================================================================



USERS_FILE = "users_db.json"
PAYMENTS_FILE = "payments_db.json"
ACCOUNTS_FILE = "accounts.json"
DEVICES_FILE = "devices.json"
TOKEN_CACHE_FILE = "token_cache.json"

FAMPAY_UPI_ID = "govindmurmu@fam"  # 👈 Your active FamPay / UPI ID
FAMPAY_MERCHANT_NAME = "PREX CODER"

# Usernames automatically granted Admin panel access
ADMIN_USERNAMES = ["123"]

SUBSCRIPTION_PLANS = {
    "plan_24h": {
        "id": "plan_24h",
        "name": "Starter Pass",
        "duration": 86400,        # 24 Hours
        "duration_label": "24 Hours",
        "price": 29,
        "max_accounts": 1
    },
    "plan_3d": {
        "id": "plan_3d",
        "name": "Grinder Pass",
        "duration": 259200,       # 3 Days
        "duration_label": "3 Days",
        "price": 69,
        "max_accounts": 2
    },
    "plan_7d": {
        "id": "plan_7d",
        "name": "Veteran Pass",
        "duration": 604800,       # 7 Days
        "duration_label": "7 Days",
        "price": 129,
        "max_accounts": 4
    },
    "plan_30d": {
        "id": "plan_30d",
        "name": "Overlord Pass",
        "duration": 2592000,      # 30 Days
        "duration_label": "30 Days",
        "price": 349,
        "max_accounts": 10
    }
}

EXP_TABLE: Dict[int, int] = {
    1: 0, 2: 48, 3: 202, 4: 544, 5: 1012, 6: 1844, 7: 2792, 8: 3800,
    9: 4870, 10: 6004, 11: 7192, 12: 8448, 13: 9760, 14: 11140, 15: 12566,
    16: 14060, 17: 15610, 18: 17224, 19: 18902, 20: 20632, 21: 22424, 22: 24278,
    23: 26192, 24: 28166, 25: 30200, 26: 32294, 27: 34448, 28: 37804, 29: 41274,
    30: 44870, 31: 48582, 32: 53394, 33: 58566, 34: 64096, 35: 69994, 36: 76460,
    37: 83506, 38: 91128, 39: 99322, 40: 108092, 41: 120144, 42: 133266, 43: 147472,
    44: 162760, 45: 179126, 46: 196572, 47: 215368, 48: 235516, 49: 257010, 50: 279860,
    51: 304056, 52: 348318, 53: 394982, 54: 444044, 55: 495508, 56: 549364, 57: 633756,
    58: 721744, 59: 813336, 60: 908522, 61: 1041438, 62: 1180352, 63: 1325266,
    64: 1476184, 65: 1634300, 66: 1840946, 67: 2056594, 68: 2281242, 69: 2514880,
    70: 2757530, 71: 3059506, 72: 3372284, 73: 3699456, 74: 4041030, 75: 4397002,
    76: 4829104, 77: 5282204, 78: 5756304, 79: 6251408, 80: 6776502, 81: 7381324,
    82: 8043154, 83: 8752982, 84: 9510808, 85: 10316338, 86: 11277190, 87: 12291748,
    88: 13360304, 89: 14482858, 90: 15659418, 91: 17026708, 92: 18453950, 93: 19941280,
    94: 21488570, 95: 23095858, 96: 24763138, 97: 26490428, 98: 28378704, 99: 30124996,
    100: 32032884
}

def calculate_level_progress(level: int, current_exp: int) -> Dict[str, Any]:
    level = max(1, level)
    next_level = min(100, level + 1)
    base_exp = EXP_TABLE.get(level, 0)
    target_exp = EXP_TABLE.get(next_level, base_exp + 50000)
    needed = max(1, target_exp - base_exp)
    earned = max(0, current_exp - base_exp)
    remaining = max(0, target_exp - current_exp)
    progress_pct = min(100.0, max(0.0, (earned / needed) * 100.0))
    return {
        "next_level": next_level,
        "base_exp": base_exp,
        "target_exp": target_exp,
        "needed_for_level": needed,
        "earned_in_level": earned,
        "remaining_exp": remaining,
        "progress_pct": round(progress_pct, 1)
    }

def hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

class BotState:
    def __init__(self):
        self.accounts: Dict[str, Dict[str, Any]] = {}
        self.user_logs: Dict[str, List[Dict[str, Any]]] = {}
        self.global_logs: List[Dict[str, Any]] = []
        self.account_owners: Dict[str, str] = {}
        self.account_workers: Dict[str, asyncio.Task] = {}
        self.account_token_map: Dict[str, str] = {}
        self.auth_to_game_id: Dict[str, str] = {}
        self.game_to_auth_id: Dict[str, str] = {}
        self.paused_accounts: set = set()
        self.refresh_callbacks: Dict[str, Any] = {}
        self.account_credentials: Dict[str, Dict[str, Any]] = {}
        self.active_writers: Dict[str, set] = {}
        self.user_sessions: Dict[str, str] = {}
        self.start_time = time.time()
        self.total_matches = 0
        self.total_matches_started = 0
        self.total_gained_exp = 0

    def load_users_db(self) -> Dict[str, Any]:
        if not os.path.exists(USERS_FILE):
            with open(USERS_FILE, "w", encoding="utf-8") as f:
                json.dump({}, f)
            return {}
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_users_db(self, db: Dict[str, Any]):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2)

    def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        db = self.load_users_db()
        return db.get(username.lower().strip())

    def update_user(self, username: str, user_data: Dict[str, Any]):
        db = self.load_users_db()
        db[username.lower().strip()] = user_data
        self.save_users_db(db)

    def is_admin(self, username: str) -> bool:
        if not username:
            return False
        u = username.lower().strip()
        if u in ADMIN_USERNAMES:
            return True
        user = self.get_user(u)
        return bool(user and user.get("is_admin"))

    def is_user_subscribed(self, username: str) -> Tuple[bool, Optional[Dict[str, Any]], int]:
        user = self.get_user(username)
        if not user:
            return False, None, 0
        sub = user.get("subscription")
        if not sub:
            return False, None, 0
        expires_at = sub.get("expires_at", 0)
        remaining = int(expires_at - time.time())
        if remaining > 0:
            return True, sub, remaining
        return False, sub, 0

    def register_writer(self, uid: str, writer):
        uid_str = str(uid)
        if uid_str not in self.active_writers:
            self.active_writers[uid_str] = set()
        self.active_writers[uid_str].add(writer)

    def unregister_writer(self, uid: str, writer):
        uid_str = str(uid)
        if uid_str in self.active_writers:
            self.active_writers[uid_str].discard(writer)
            if not self.active_writers[uid_str]:
                self.active_writers.pop(uid_str, None)

    def close_writers_for_account(self, uid: str):
        uid_str = str(uid)
        candidates = {uid_str}
        if uid_str in self.auth_to_game_id:
            candidates.add(str(self.auth_to_game_id[uid_str]))
        if uid_str in self.game_to_auth_id:
            candidates.add(str(self.game_to_auth_id[uid_str]))
        if uid_str in self.account_token_map:
            mapped = self.account_token_map[uid_str]
            candidates.add(str(mapped))
            candidates.add(str(mapped)[:16])

        for c in list(candidates):
            writers = list(self.active_writers.get(c, []))
            for w in writers:
                try:
                    if hasattr(w, "close") and not w.is_closing():
                        w.close()
                except Exception:
                    pass
            self.active_writers.pop(c, None)

    def log(self, message: str, level: str = "info", uid: Optional[str] = None, username: Optional[str] = None):
    entry = {
        "time": fmt_time(),              # 👈 IST time
        "datetime": fmt_datetime(),      # 👈 Full IST datetime (optional)
        "level": level,
        "message": message,
        "uid": str(uid) if uid else None
        }
        self.global_logs.append(entry)
        if len(self.global_logs) > 500:
            self.global_logs.pop(0)

        target_user = username
        if not target_user and uid:
            uid_str = str(uid)
            target_user = self.account_owners.get(uid_str) or self.account_owners.get(self.auth_to_game_id.get(uid_str, ""))

        if target_user:
            if target_user not in self.user_logs:
                self.user_logs[target_user] = []
            self.user_logs[target_user].append(entry)
            if len(self.user_logs[target_user]) > 150:
                self.user_logs[target_user].pop(0)

    def register_account(self, uid: str, nickname: str, region: str, level: int, exp: int,
                         likes: int = 0, token: Optional[str] = None, auth_uid: Optional[str] = None,
                         owner: Optional[str] = None):
        uid_str = str(uid)
        auth_uid_str = str(auth_uid) if auth_uid else self.game_to_auth_id.get(uid_str, "")
        if auth_uid_str:
            self.auth_to_game_id[auth_uid_str] = uid_str
            self.game_to_auth_id[uid_str] = auth_uid_str
            self.account_token_map[auth_uid_str] = uid_str
            self.account_token_map[uid_str] = auth_uid_str
        if token:
            self.account_token_map[uid_str] = token
            self.account_token_map[token[:16]] = uid_str
            if auth_uid_str:
                self.account_token_map[auth_uid_str] = token

        if owner:
            self.account_owners[uid_str] = owner
            if auth_uid_str:
                self.account_owners[auth_uid_str] = owner
            if token:
                self.account_owners[token[:16]] = owner

        prog = calculate_level_progress(level or 1, exp)
        lvl_val = level or 1
        acc_mode = "BR" if lvl_val < 3 else "LONE_WOLF"

        if uid_str not in self.accounts:
            self.accounts[uid_str] = {
                "uid": uid_str,
                "auth_uid": auth_uid_str or "",
                "owner": owner or self.account_owners.get(uid_str, "admin"),
                "nickname": nickname or f"Player_{uid_str[:6]}",
                "region": region or "BD",
                "level": lvl_val,
                "next_level": prog["next_level"],
                "mode": acc_mode,
                "initial_exp": exp,
                "current_exp": exp,
                "gained_exp": 0,
                "remaining_exp": prog["remaining_exp"],
                "target_exp": prog["target_exp"],
                "needed_for_level": prog["needed_for_level"],
                "earned_in_level": prog["earned_in_level"],
                "progress_pct": prog["progress_pct"],
                "likes": likes or 0,
                "status": "PAUSED" if self.is_paused(uid_str) else "ONLINE",
                "matches_played": 0,
                "active_matches": 0,
                "last_match_time": None,
                "token": token or "",
                "start_time": time.time(),
                "is_paused": self.is_paused(uid_str),
                "last_updated": time.strftime("%H:%M:%S")
            }
        else:
            acc = self.accounts[uid_str]
            if owner:
                acc["owner"] = owner
            if auth_uid_str:
                acc["auth_uid"] = auth_uid_str
            if nickname:
                acc["nickname"] = nickname
            if region:
                acc["region"] = region
            if level:
                acc["level"] = level
            acc["current_exp"] = exp
            acc["gained_exp"] = max(0, exp - acc["initial_exp"])
            acc["next_level"] = prog["next_level"]
            acc["remaining_exp"] = prog["remaining_exp"]
            acc["progress_pct"] = prog["progress_pct"]
            acc["likes"] = likes
            acc["last_updated"] = time.strftime("%H:%M:%S")

    def is_paused(self, uid: str) -> bool:
        uid_str = str(uid)
        return (uid_str in self.paused_accounts or
                self.auth_to_game_id.get(uid_str) in self.paused_accounts or
                self.game_to_auth_id.get(uid_str) in self.paused_accounts)

    def toggle_pause(self, uid: str) -> bool:
        uid_str = str(uid)
        candidates = {uid_str}
        if uid_str in self.auth_to_game_id:
            candidates.add(self.auth_to_game_id[uid_str])
        if uid_str in self.game_to_auth_id:
            candidates.add(self.game_to_auth_id[uid_str])

        is_now_paused = not self.is_paused(uid_str)
        for c in candidates:
            if is_now_paused:
                self.paused_accounts.add(c)
                self.close_writers_for_account(c)
            else:
                self.paused_accounts.discard(c)

        for c in candidates:
            if c in self.accounts:
                self.accounts[c]["is_paused"] = is_now_paused
                self.accounts[c]["status"] = "PAUSED" if is_now_paused else "ONLINE"

        self.log(f"{'⏸ Paused' if is_now_paused else '▶ Resumed'} matchmaking for {uid_str}",
                 "warning" if is_now_paused else "success", uid_str)
        return is_now_paused

    def toggle_pause_user_accounts(self, username: str) -> bool:
        user_accs = [k for k, v in self.accounts.items() if v.get("owner") == username]
        any_active = any(not self.is_paused(k) for k in user_accs)
        for k in user_accs:
            if any_active and not self.is_paused(k):
                self.toggle_pause(k)
            elif not any_active and self.is_paused(k):
                self.toggle_pause(k)
        return any_active

    def update_exp(self, uid: str, current_exp: int, level: Optional[int] = None):
        uid_str = str(uid)
        if uid_str in self.accounts:
            acc = self.accounts[uid_str]
            old_exp = acc["current_exp"]
            acc["current_exp"] = current_exp
            if level is not None and level > 0:
                acc["level"] = level
            acc["gained_exp"] = max(0, current_exp - acc["initial_exp"])
            prog = calculate_level_progress(acc["level"], current_exp)
            acc["next_level"] = prog["next_level"]
            acc["remaining_exp"] = prog["remaining_exp"]
            acc["progress_pct"] = prog["progress_pct"]
            acc["last_updated"] = time.strftime("%H:%M:%S")

            diff = current_exp - old_exp
            if diff > 0:
                self.log(f"★ +{diff:,} EXP Earned | Level {acc['level']} ({prog['progress_pct']}%)",
                         "success", uid_str)

    def update_status(self, uid: str, status: str, active_matches: Optional[int] = None):
        uid_str = str(uid)
        if uid_str in self.accounts:
            self.accounts[uid_str]["status"] = status
            if active_matches is not None:
                self.accounts[uid_str]["active_matches"] = active_matches
            self.accounts[uid_str]["last_updated"] = time.strftime("%H:%M:%S")

    def increment_match(self, uid: str):
        uid_str = str(uid)
        self.total_matches += 1
        if uid_str in self.accounts:
            self.accounts[uid_str]["matches_played"] += 1
            self.accounts[uid_str]["last_match_time"] = time.strftime("%H:%M:%S")
            self.log(f"⚔ Match #{self.accounts[uid_str]['matches_played']} Finished", "info", uid_str)

    def increment_match_started(self):
        self.total_matches_started += 1

    def get_user_from_request(self, request: web.Request) -> Optional[str]:
        session_token = request.cookies.get("saas_session")
        if not session_token:
            auth_hdr = request.headers.get("Authorization", "")
            if auth_hdr.startswith("Bearer "):
                session_token = auth_hdr.split(" ")[1]
        return self.user_sessions.get(session_token) if session_token else None

bot_state = BotState()

# ==================== ROUTE HANDLERS ====================
async def handle_index(request: web.Request) -> web.Response:
    if os.path.exists(TEMPLATE_PATH):
        with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
            return web.Response(text=f.read(), content_type="text/html", charset="utf-8")
    return web.Response(text="<h1>index.html template not found.</h1>", content_type="text/html")


## qr ka liya
async def handle_static_file(request: web.Request) -> web.Response:
    """Serve any file from the project root folder (qr.jpeg, etc.)"""
    filename = request.match_info.get('filename', '')
    # Security: block path traversal
    if '..' in filename or filename.startswith('/'):
        return web.Response(status=403, text="Forbidden")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_dir, filename)
    
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return web.Response(status=404, text=f"Not Found: {filename}")
    
    # Detect content type by extension
    ext = os.path.splitext(filename)[1].lower()
    content_types = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
        '.svg': 'image/svg+xml',
        '.ico': 'image/x-icon',
        '.css': 'text/css',
        '.js': 'application/javascript',
        '.json': 'application/json',
        '.txt': 'text/plain',
    }
    ctype = content_types.get(ext, 'application/octet-stream')
    
    with open(file_path, 'rb') as f:
        return web.Response(body=f.read(), content_type=ctype)

async def handle_register(request: web.Request) -> web.Response:
    try:
        data = await request.json()
        username = str(data.get("username", "")).strip().lower()
        password = str(data.get("password", "")).strip()

        if len(username) < 3:
            return web.json_response({"status": "error", "error": "Username must be at least 3 characters."})
        if len(password) < 4:
            return web.json_response({"status": "error", "error": "Password must be at least 4 characters."})
        if bot_state.get_user(username):
            return web.json_response({"status": "error", "error": "Username already exists. Please sign in."})

        is_admin_user = username in ADMIN_USERNAMES
        user_obj = {
            "username": username,
            "password_hash": hash_pw(password),
            "created_at": time.time(),
            "subscription": None,
            "is_admin": is_admin_user
        }
        bot_state.update_user(username, user_obj)

        token = str(uuid.uuid4())
        bot_state.user_sessions[token] = username
        resp = web.json_response({"status": "ok", "username": username, "token": token, "is_admin": is_admin_user})
        resp.set_cookie("saas_session", token, max_age=86400 * 30, httponly=True)
        bot_state.log(f"User registered: {username}", "success", username=username)
        return resp
    except Exception as e:
        return web.json_response({"status": "error", "error": str(e)})

async def handle_login(request: web.Request) -> web.Response:
    try:
        data = await request.json()
        username = str(data.get("username", "")).strip().lower()
        password = str(data.get("password", "")).strip()

        user = bot_state.get_user(username)
        if not user or user.get("password_hash") != hash_pw(password):
            return web.json_response({"status": "error", "error": "Invalid username or password."})

        token = str(uuid.uuid4())
        bot_state.user_sessions[token] = username
        is_adm = bot_state.is_admin(username)
        resp = web.json_response({"status": "ok", "username": username, "token": token, "is_admin": is_adm})
        resp.set_cookie("saas_session", token, max_age=86400 * 30, httponly=True)
        bot_state.log(f"User logged in: {username}", "info", username=username)
        return resp
    except Exception as e:
        return web.json_response({"status": "error", "error": str(e)})

async def handle_logout(request: web.Request) -> web.Response:
    token = request.cookies.get("saas_session")
    if token in bot_state.user_sessions:
        del bot_state.user_sessions[token]
    resp = web.json_response({"status": "ok"})
    resp.del_cookie("saas_session")
    return resp

async def handle_get_me(request: web.Request) -> web.Response:
    username = bot_state.get_user_from_request(request)
    if not username:
        return web.json_response({"authenticated": False})
    
    is_sub, plan_info, remaining_sec = bot_state.is_user_subscribed(username)
    is_adm = bot_state.is_admin(username)

    # Check for pending payments submitted by this user
    pending_order = None
    if os.path.exists(PAYMENTS_FILE):
        try:
            with open(PAYMENTS_FILE, "r", encoding="utf-8") as f:
                pdb = json.load(f)
            for ord_id, o in pdb.items():
                if o.get("username") == username and o.get("status") == "WAITING_APPROVAL":
                    pending_order = o
                    break
        except Exception:
            pass

    return web.json_response({
        "authenticated": True,
        "username": username,
        "is_admin": is_adm,
        "is_subscribed": is_sub,
        "subscription": plan_info,
        "remaining_seconds": remaining_sec,
        "pending_order": pending_order,
        "plans": SUBSCRIPTION_PLANS,
        "fampay_upi": FAMPAY_UPI_ID,
        "merchant_name": FAMPAY_MERCHANT_NAME
    })

# ---------- FAMPAY & ADMIN PAYMENT WORKFLOW ----------
async def handle_create_order(request: web.Request) -> web.Response:
    username = bot_state.get_user_from_request(request)
    if not username:
        return web.json_response({"status": "error", "error": "Login required"}, status=401)
    try:
        data = await request.json()
        plan_id = str(data.get("plan_id", ""))
        if plan_id not in SUBSCRIPTION_PLANS:
            return web.json_response({"status": "error", "error": "Invalid plan selected."})

        plan = SUBSCRIPTION_PLANS[plan_id]
        order_ref = f"FAM{int(time.time())}{random.randint(100, 999)}"
        amount = plan["price"]
        upi_link = f"upi://pay?pa={FAMPAY_UPI_ID}&pn={FAMPAY_MERCHANT_NAME}&am={amount}&cu=INR&tn=Order_{order_ref}"

        payments_db = {}
        if os.path.exists(PAYMENTS_FILE):
            try:
                with open(PAYMENTS_FILE, "r", encoding="utf-8") as f:
                    payments_db = json.load(f)
            except Exception:
                payments_db = {}

        payments_db[order_ref] = {
            "order_id": order_ref,
            "username": username,
            "plan_id": plan_id,
            "plan_name": plan["name"],
            "duration_label": plan["duration_label"],
            "amount": amount,
            "status": "PENDING",
            "utr": "",
            "created_at": time.time()
        }
        with open(PAYMENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(payments_db, f, indent=2)

        return web.json_response({
            "status": "ok",
            "order_id": order_ref,
            "amount": amount,
            "upi_id": FAMPAY_UPI_ID,
            "merchant": FAMPAY_MERCHANT_NAME,
            "upi_link": upi_link,
            "plan_name": plan["name"],
            "plan_duration": plan["duration_label"]
        })
    except Exception as e:
        return web.json_response({"status": "error", "error": str(e)})

async def handle_verify_payment(request: web.Request) -> web.Response:
    """User submits FamPay UTR reference -> enters WAITING_APPROVAL status."""
    username = bot_state.get_user_from_request(request)
    if not username:
        return web.json_response({"status": "error", "error": "Login required"}, status=401)
    try:
        data = await request.json()
        order_id = str(data.get("order_id", "")).strip()
        utr = str(data.get("utr", "")).strip()

        if len(utr) < 8:
            return web.json_response({"status": "error", "error": "Please enter a valid 12-digit FamPay/UPI UTR or Reference Number."})

        payments_db = {}
        if os.path.exists(PAYMENTS_FILE):
            try:
                with open(PAYMENTS_FILE, "r", encoding="utf-8") as f:
                    payments_db = json.load(f)
            except Exception:
                pass

        order = payments_db.get(order_id)
        if not order:
            return web.json_response({"status": "error", "error": "Order reference not found."})

        # Put under admin verification review
        order["status"] = "WAITING_APPROVAL"
        order["utr"] = utr
        order["submitted_at"] = time.time()
        payments_db[order_id] = order
        with open(PAYMENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(payments_db, f, indent=2)

        bot_state.log(f"Payment UTR ({utr}) submitted by {username}. Waiting for admin approval.", "warning", username=username)

        return web.json_response({
            "status": "ok",
            "message": "Payment details submitted! Admin will verify and activate your pass shortly.",
            "order_status": "WAITING_APPROVAL"
        })
    except Exception as e:
        return web.json_response({"status": "error", "error": str(e)})

# ---------- ADMIN PAYMENT CONTROLS ----------
async def handle_admin_get_payments(request: web.Request) -> web.Response:
    username = bot_state.get_user_from_request(request)
    if not bot_state.is_admin(username):
        return web.json_response({"status": "error", "error": "Admin privileges required"}, status=403)

    payments_list = []
    if os.path.exists(PAYMENTS_FILE):
        try:
            with open(PAYMENTS_FILE, "r", encoding="utf-8") as f:
                pdb = json.load(f)
            payments_list = list(pdb.values())
            # Sort newest first
            payments_list.sort(key=lambda x: x.get("created_at", 0), reverse=True)
        except Exception:
            payments_list = []

    return web.json_response({"status": "ok", "payments": payments_list})

async def handle_admin_approve_payment(request: web.Request) -> web.Response:
    username = bot_state.get_user_from_request(request)
    if not bot_state.is_admin(username):
        return web.json_response({"status": "error", "error": "Admin privileges required"}, status=403)

    try:
        data = await request.json()
        order_id = str(data.get("order_id", "")).strip()

        if not os.path.exists(PAYMENTS_FILE):
            return web.json_response({"status": "error", "error": "No payment records found."})

        with open(PAYMENTS_FILE, "r", encoding="utf-8") as f:
            payments_db = json.load(f)

        order = payments_db.get(order_id)
        if not order:
            return web.json_response({"status": "error", "error": "Order not found."})

        target_username = order.get("username")
        plan_id = order.get("plan_id")
        plan = SUBSCRIPTION_PLANS.get(plan_id)
        if not plan:
            return web.json_response({"status": "error", "error": "Plan metadata not found."})

        user = bot_state.get_user(target_username)
        if not user:
            return web.json_response({"status": "error", "error": f"User '{target_username}' not found."})

        # Calculate extension or new expiry
        cur_expires = user.get("subscription", {}).get("expires_at", 0) if user.get("subscription") else 0
        base_time = max(time.time(), cur_expires)
        new_expiry = base_time + plan["duration"]

        user["subscription"] = {
            "plan_id": plan["id"],
            "plan_name": plan["name"],
            "duration_label": plan["duration_label"],
            "activated_at": time.time(),
            "expires_at": new_expiry,
            "max_accounts": plan["max_accounts"]
        }
        bot_state.update_user(target_username, user)

        order["status"] = "APPROVED"
        order["approved_by"] = username
        order["approved_at"] = time.time()
        payments_db[order_id] = order
        with open(PAYMENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(payments_db, f, indent=2)

        bot_state.log(f"💎 Plan Approved by Admin for {target_username}: {plan['name']} ({plan['duration_label']})", "success", username=target_username)
        return web.json_response({"status": "ok", "message": f"Payment approved for {target_username}!"})
    except Exception as e:
        return web.json_response({"status": "error", "error": str(e)})

async def handle_admin_reject_payment(request: web.Request) -> web.Response:
    username = bot_state.get_user_from_request(request)
    if not bot_state.is_admin(username):
        return web.json_response({"status": "error", "error": "Admin privileges required"}, status=403)

    try:
        data = await request.json()
        order_id = str(data.get("order_id", "")).strip()

        if not os.path.exists(PAYMENTS_FILE):
            return web.json_response({"status": "error", "error": "No payment records found."})

        with open(PAYMENTS_FILE, "r", encoding="utf-8") as f:
            payments_db = json.load(f)

        order = payments_db.get(order_id)
        if not order:
            return web.json_response({"status": "error", "error": "Order not found."})

        order["status"] = "REJECTED"
        order["rejected_by"] = username
        order["rejected_at"] = time.time()
        payments_db[order_id] = order
        with open(PAYMENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(payments_db, f, indent=2)

        bot_state.log(f"Payment {order_id} was rejected by Admin.", "error", username=order.get("username"))
        return web.json_response({"status": "ok", "message": f"Payment {order_id} marked as rejected."})
    except Exception as e:
        return web.json_response({"status": "error", "error": str(e)})

# ---------- USER STATS & ACTIONS ----------
async def handle_get_stats(request: web.Request) -> web.Response:
    username = bot_state.get_user_from_request(request)
    if not username:
        return web.json_response({"status": "error", "error": "Unauthorized"}, status=401)

    is_sub, plan_info, remaining_sec = bot_state.is_user_subscribed(username)
    user_accounts = [acc for acc in bot_state.accounts.values() if acc.get("owner") == username]
    user_accounts.sort(key=lambda x: x.get("gained_exp", 0), reverse=True)

    total_gained = sum(acc.get("gained_exp", 0) for acc in user_accounts)
    total_matches = sum(acc.get("matches_played", 0) for acc in user_accounts)
    active_matches = sum(acc.get("active_matches", 0) for acc in user_accounts)
    user_logs = bot_state.user_logs.get(username, [])

    return web.json_response({
        "username": username,
        "is_subscribed": is_sub,
        "remaining_seconds": remaining_sec,
        "plan": plan_info,
        "total_accounts": len(user_accounts),
        "total_matches": total_matches,
        "total_active_matches": active_matches,
        "total_gained_exp": total_gained,
        "accounts": user_accounts,
        "logs": user_logs[-80:],
        "uptime": int(time.time() - bot_state.start_time)
    })

async def handle_add_account(request: web.Request) -> web.Response:
    username = bot_state.get_user_from_request(request)
    if not username:
        return web.json_response({"status": "error", "error": "Login required"}, status=401)

    is_sub, plan, _ = bot_state.is_user_subscribed(username)
    if not is_sub:
        return web.json_response({
            "status": "error",
            "error": "🔒 ACTIVE PLAN REQUIRED: Please select a pass and submit your payment for admin verification first."
        }, status=403)

    user_accs = [acc for acc in bot_state.accounts.values() if acc.get("owner") == username]
    max_allowed = plan.get("max_accounts", 1)
    if len(user_accs) >= max_allowed:
        return web.json_response({
            "status": "error",
            "error": f"Quota limit reached. Your {plan['plan_name']} allows up to {max_allowed} account(s)."
        }, status=403)

    try:
        data = await request.json()
        accounts_file = ACCOUNTS_FILE
        existing = []
        if os.path.exists(accounts_file):
            try:
                with open(accounts_file, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                existing = []

        identifier = ""
        if "uid" in data and "password" in data:
            uid = str(data["uid"]).strip()
            pwd = str(data["password"]).strip()
            if not uid or not pwd:
                return web.json_response({"status": "error", "error": "UID and Password required"})

            if uid in bot_state.account_workers:
                try:
                    bot_state.account_workers[uid].cancel()
                except Exception:
                    pass
                bot_state.account_workers.pop(uid, None)

            existing = [acc for acc in existing if str(acc.get("uid", "")) != uid]
            existing.append({"uid": uid, "password": pwd, "owner": username})
            identifier = uid
            bot_state.account_owners[uid] = username

        elif "token" in data:
            token = str(data["token"]).strip()
            if not token:
                return web.json_response({"status": "error", "error": "Token required"})

            tok_pfx = token[:16]
            if tok_pfx in bot_state.account_workers:
                try:
                    bot_state.account_workers[tok_pfx].cancel()
                except Exception:
                    pass
                bot_state.account_workers.pop(tok_pfx, None)

            existing = [acc for acc in existing if acc.get("token", "") != token]
            existing.append({"token": token, "owner": username})
            identifier = f"Token_{token[:8]}..."
            bot_state.account_owners[tok_pfx] = username
        else:
            return web.json_response({"status": "error", "error": "Invalid account payload"})

        with open(accounts_file, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)

        bot_state.log(f"Account added: {identifier}", "success", username=username)
        data["owner"] = username
        if "on_account_added" in bot_state.refresh_callbacks:
            asyncio.create_task(bot_state.refresh_callbacks["on_account_added"](data))

        return web.json_response({"status": "ok"})
    except Exception as e:
        return web.json_response({"status": "error", "error": str(e)})

async def handle_delete_account(request: web.Request) -> web.Response:
    username = bot_state.get_user_from_request(request)
    if not username:
        return web.json_response({"status": "error", "error": "Unauthorized"}, status=401)

    try:
        data = await request.json()
        req_uid = str(data.get("uid", "")).strip()
        if not req_uid:
            return web.json_response({"status": "error", "error": "UID required"})

        candidate_ids = {req_uid}
        if req_uid in bot_state.game_to_auth_id:
            candidate_ids.add(str(bot_state.game_to_auth_id[req_uid]))
        if req_uid in bot_state.auth_to_game_id:
            candidate_ids.add(str(bot_state.auth_to_game_id[req_uid]))
        if req_uid in bot_state.account_token_map:
            candidate_ids.add(str(bot_state.account_token_map[req_uid]))
            candidate_ids.add(str(bot_state.account_token_map[req_uid])[:16])

        is_owner = any(bot_state.account_owners.get(c) == username for c in candidate_ids)
        acc_entry = bot_state.accounts.get(req_uid)
        if acc_entry and acc_entry.get("owner") == username:
            is_owner = True
        if bot_state.is_admin(username):
            is_owner = True

        if not is_owner:
            return web.json_response({"status": "error", "error": "Permission denied for this account."}, status=403)

        for cid in candidate_ids:
            bot_state.close_writers_for_account(cid)

        for cid in candidate_ids:
            worker = bot_state.account_workers.pop(cid, None)
            if worker:
                try:
                    worker.cancel()
                except Exception:
                    pass

        for cid in candidate_ids:
            bot_state.accounts.pop(cid, None)
            bot_state.account_credentials.pop(cid, None)
            bot_state.auth_to_game_id.pop(cid, None)
            bot_state.game_to_auth_id.pop(cid, None)
            bot_state.account_token_map.pop(cid, None)
            bot_state.account_owners.pop(cid, None)

        if os.path.exists(ACCOUNTS_FILE):
            try:
                with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                    accs = json.load(f)
                accs = [a for a in accs if str(a.get("uid", "")) not in candidate_ids and
                        str(a.get("token", ""))[:16] not in candidate_ids]
                with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
                    json.dump(accs, f, indent=2)
            except Exception:
                pass

        if "on_account_deleted" in bot_state.refresh_callbacks:
            try:
                asyncio.create_task(bot_state.refresh_callbacks["on_account_deleted"](list(candidate_ids)))
            except Exception:
                pass

        bot_state.log(f"Account {req_uid} terminated and deleted.", "warning", username=username)
        return web.json_response({"status": "ok"})
    except Exception as e:
        return web.json_response({"status": "error", "error": str(e)})

async def handle_toggle_pause(request: web.Request) -> web.Response:
    username = bot_state.get_user_from_request(request)
    if not username:
        return web.json_response({"status": "error", "error": "Unauthorized"}, status=401)
    data = await request.json()
    uid = str(data.get("uid", "")).strip()
    is_paused = bot_state.toggle_pause(uid)
    return web.json_response({"status": "ok", "is_paused": is_paused})

async def handle_toggle_pause_all(request: web.Request) -> web.Response:
    username = bot_state.get_user_from_request(request)
    if not username:
        return web.json_response({"status": "error", "error": "Unauthorized"}, status=401)
    all_paused = bot_state.toggle_pause_user_accounts(username)
    return web.json_response({"status": "ok", "all_paused": all_paused})

async def handle_clear_logs(request: web.Request) -> web.Response:
    username = bot_state.get_user_from_request(request)
    if username and username in bot_state.user_logs:
        bot_state.user_logs[username].clear()
    return web.json_response({"status": "ok"})

async def handle_refresh_account(request: web.Request) -> web.Response:
    username = bot_state.get_user_from_request(request)
    if not username:
        return web.json_response({"status": "error", "error": "Unauthorized"}, status=401)
    data = await request.json()
    uid = str(data.get("uid", "")).strip()
    if "on_refresh_account" in bot_state.refresh_callbacks:
        asyncio.create_task(bot_state.refresh_callbacks["on_refresh_account"](uid))
    return web.json_response({"status": "ok"})

async def start_web_dashboard(host: str = "0.0.0.0", port: int = 20331):
    app = web.Application()
    app.router.add_get("/", handle_index)
    app.router.add_post("/api/auth/register", handle_register)
    app.router.add_post("/api/auth/login", handle_login)
    app.router.add_post("/api/auth/logout", handle_logout)
    app.router.add_get("/api/auth/me", handle_get_me)
    
    # FamPay & Admin Payment Routes
    app.router.add_post("/api/payment/create", handle_create_order)
    app.router.add_post("/api/payment/verify", handle_verify_payment)
    app.router.add_get("/api/admin/payments", handle_admin_get_payments)
    app.router.add_post("/api/admin/payment/approve", handle_admin_approve_payment)
    app.router.add_post("/api/admin/payment/reject", handle_admin_reject_payment)
    
    # Bot Control Routes
    app.router.add_get("/api/stats", handle_get_stats)
    app.router.add_post("/api/account/add", handle_add_account)
    app.router.add_post("/api/account/delete", handle_delete_account)
    app.router.add_post("/api/account/pause", handle_toggle_pause)
    app.router.add_post("/api/account/pause_all", handle_toggle_pause_all)
    app.router.add_post("/api/account/refresh", handle_refresh_account)
    app.router.add_post("/api/logs/clear", handle_clear_logs)

    # 👇 YEH LINE ADD KARO — Static file serving (qr.jpeg ke liye)
    app.router.add_get("/{filename}", handle_static_file)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    return runner
