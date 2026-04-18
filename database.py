import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date
import json
import hashlib
import hmac

# --- КОНСТАНТЫ КОЛОНОК ---
COL_EMAIL      = 1
COL_NAME       = 2
COL_PWD        = 3
COL_MSGS_TODAY = 4
COL_LAST_DATE  = 5
COL_PROFILE    = 6
COL_HISTORY    = 7
COL_VIP        = 8

# ---------------------------------------------------------------------------
# ХЕШИРОВАНИЕ ПАРОЛЕЙ (Усилено HMAC + Соль Системы)
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    """Хеширование с использованием HMAC и системного ключа (Соли)."""
    secret = st.secrets["SECRET_KEY"].encode("utf-8")
    return hmac.new(secret, password.encode("utf-8"), hashlib.sha256).hexdigest()

def check_password(plain: str, stored: str) -> bool:
    """Безопасное сравнение через hmac.compare_digest.
    Поддерживает оба формата: хеш (новые аккаунты) и открытый текст (старые)."""
    hashed = hash_password(plain)
    # Хеш SHA-256 — 64 символа hex
    if len(stored) == 64 and all(c in "0123456789abcdef" for c in stored.lower()):
        return hmac.compare_digest(hashed, stored)
    # Старый аккаунт с открытым паролем — плавная миграция
    return hmac.compare_digest(plain, stored)

# ---------------------------------------------------------------------------
# ТОКЕН ОТПИСКИ (HMAC-подписанный, без хранения в БД)
# ---------------------------------------------------------------------------
def _unsub_secret() -> str:
    return st.secrets["UNSUB_SECRET"]

def make_unsub_token(email: str) -> str:
    """Генерирует одноразовый HMAC-токен для конкретного email."""
    return hmac.new(
        _unsub_secret().encode(),
        email.encode(),
        hashlib.sha256
    ).hexdigest()[:32]

def verify_unsub_token(email: str, token: str) -> bool:
    """Проверяет, что токен принадлежит именно этому email."""
    expected = make_unsub_token(email)
    return hmac.compare_digest(expected, token)

# ---------------------------------------------------------------------------
# КЭШИРОВАННЫЙ КЛИЕНТ GSPREAD И БД (Защита от лимитов Google API)
# ---------------------------------------------------------------------------
@st.cache_resource(ttl=3600)
def get_gspread_client():
    creds_dict = None
    if "gcp_service_account" in st.secrets:
        raw = st.secrets["gcp_service_account"]
        if hasattr(raw, "to_dict"):  creds_dict = raw.to_dict()
        elif isinstance(raw, dict):  creds_dict = raw
        elif isinstance(raw, str):
            try: creds_dict = json.loads(raw)
            except: pass

    if not creds_dict and "private_key" in st.secrets:
        keys = ["type", "project_id", "private_key_id", "private_key", "client_email",
                "client_id", "auth_uri", "token_uri",
                "auth_provider_x509_cert_url", "client_x509_cert_url"]
        creds_dict = {k: st.secrets.get(k) for k in keys}

    if not creds_dict:
        print("DB Error: credentials not found in secrets")
        return None

    try:
        scope = ["https://spreadsheets.google.com/feeds",
                 "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        print(f"Auth Error: {e}")
        return None

@st.cache_resource(ttl=3600)
def get_db():
    client = get_gspread_client()
    if not client:
        raise RuntimeError("DB недоступна: клиент gspread не создан")
    try:
        return client.open("MUKTI_DB").sheet1
    except Exception as e:
        print(f"Open DB Error: {e}")
        raise RuntimeError(f"DB недоступна: {e}")

# ---------------------------------------------------------------------------
# САНИТИЗАЦИЯ (защита от инъекций формул Google Sheets)
# ---------------------------------------------------------------------------
def sanitize(value):
    if isinstance(value, str):
        val = value.strip()
        if val.startswith(("=", "+", "-", "@")):
            return "'" + val
        return val
    return value

# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------
def load_user(email: str):
    sheet = get_db()
    if not sheet: return None, None
    try:
        emails = sheet.col_values(COL_EMAIL)
        email_lower = email.strip().lower()
        if email_lower in emails:
            r_num = emails.index(email_lower) + 1
            return sheet.row_values(r_num), r_num
    except Exception as e:
        print(f"Load User Error: {e}")
    return None, None

def register_user(email: str, username: str, password: str):
    sheet = get_db()
    if not sheet: return "DB_ERROR"
    row, _ = load_user(email)
    if row: return "TAKEN"
    try:
        new_row = [
            sanitize(email.lower()),
            sanitize(username),
            hash_password(password),
            0,
            str(date.today()),
            "{}",
            "[]",
            "FALSE"
        ]
        sheet.append_row(new_row)
        return "OK"
    except Exception as e:
        print(f"Register Error: {e}")
        return "DB_ERROR"

def update_field(row_num: int, col_num: int, value):
    sheet = get_db()
    if sheet:
        try: sheet.update_cell(row_num, col_num, sanitize(value))
        except Exception as e: print(f"Update Field Error (row={row_num}, col={col_num}): {e}")

def update_profile(row_num: int, key: str, value):
    """Обновляет одно поле профиля. Для нескольких — используй update_profile_batch."""
    sheet = get_db()
    if sheet:
        try:
            current_json = sheet.cell(row_num, COL_PROFILE).value
            data = json.loads(current_json) if current_json else {}
            data[key] = sanitize(value) if isinstance(value, str) else value
            sheet.update_cell(row_num, COL_PROFILE, json.dumps(data, ensure_ascii=False))
        except Exception as e: print(f"Update Profile Error: {e}")

def update_profile_batch(row_num: int, updates: dict):
    """Пакетное обновление профиля — один API-запрос вместо нескольких."""
    sheet = get_db()
    if sheet:
        try:
            current_json = sheet.cell(row_num, COL_PROFILE).value
            data = json.loads(current_json) if current_json else {}
            for k, v in updates.items():
                data[k] = sanitize(v) if isinstance(v, str) else v
            sheet.update_cell(row_num, COL_PROFILE, json.dumps(data, ensure_ascii=False))
            return True
        except Exception as e:
            print(f"Batch Update Error: {e}")
    return False

def save_history(row_num: int, history_list: list, depth: int = 30):
    sheet = get_db()
    if sheet:
        try:
            sheet.update_cell(row_num, COL_HISTORY,
                              json.dumps(history_list[-depth:], ensure_ascii=False))
        except Exception as e: print(f"Save History Error: {e}")

def get_all_users():
    sheet = get_db()
    if not sheet: return []
    try:
        records = sheet.get_all_values()
        users = []
        for idx, row in enumerate(records):
            if not row or len(row) < 6: continue
            if row[0].lower() == "email": continue
            r_num   = idx + 1
            u_email = row[COL_EMAIL - 1]
            u_name  = row[COL_NAME - 1]
            p_json  = row[COL_PROFILE - 1]
            users.append((r_num, u_email, u_name, p_json))
        return users
    except Exception as e:
        print(f"Get All Users Error: {e}")
        return []
