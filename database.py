import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date
import json

# --- КОНСТАНТЫ КОЛОНОК (Магические числа убраны) ---
COL_EMAIL = 1
COL_NAME = 2
COL_PWD = 3
COL_MSGS_TODAY = 4
COL_LAST_DATE = 5
COL_PROFILE = 6
COL_HISTORY = 7
COL_VIP = 8

# --- КЭШИРОВАНИЕ КЛИЕНТА (Оптимизация API) ---
@st.cache_resource(ttl=3600)
def get_gspread_client():
    creds_dict = None
    if "gcp_service_account" in st.secrets:
        raw = st.secrets["gcp_service_account"]
        if hasattr(raw, "to_dict"): creds_dict = raw.to_dict()
        elif isinstance(raw, dict): creds_dict = raw
        elif isinstance(raw, str):
            try: creds_dict = json.loads(raw)
            except: pass
            
    if not creds_dict and "private_key" in st.secrets:
        creds_dict = {k: st.secrets.get(k) for k in ["type", "project_id", "private_key_id", "private_key", "client_email", "client_id", "auth_uri", "token_uri", "auth_provider_x509_cert_url", "client_x509_cert_url"]}

    if not creds_dict: return None

    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        print(f"Auth Error: {e}")
        return None

def get_db():
    client = get_gspread_client()
    if client:
        try: return client.open("MUKTI_DB").sheet1
        except Exception as e:
            print(f"Open DB Error: {e}")
    return None

# --- ВАЛИДАЦИЯ ДАННЫХ (Защита от инъекций формул Google Sheets) ---
def sanitize(value):
    if isinstance(value, str):
        val = value.strip()
        # Если строка начинается со спецсимвола формулы, ставим апостроф
        if val.startswith(('=', '+', '-', '@')):
            return "'" + val
        return val
    return value

# ИЩЕМ ПО EMAIL В 1-Й КОЛОНКЕ
def load_user(email):
    sheet = get_db()
    if not sheet: return None, None
    try:
        emails = sheet.col_values(COL_EMAIL)
        if email in emails:
            r_num = emails.index(email) + 1
            return sheet.row_values(r_num), r_num
    except Exception as e:
        print(f"Load User Error: {e}")
    return None, None

def register_user(email, username, password):
    sheet = get_db()
    if not sheet: return "DB_ERROR"
    row, _ = load_user(email)
    if row: return "TAKEN"
    try:
        new_row = [sanitize(email), sanitize(username), sanitize(password), 0, str(date.today()), "{}", "[]", "FALSE"]
        sheet.append_row(new_row)
        return "OK"
    except Exception as e:
        print(f"Register Error: {e}")
        return "DB_ERROR"

def update_field(row_num, col_num, value):
    sheet = get_db()
    if sheet:
        try: sheet.update_cell(row_num, col_num, sanitize(value))
        except Exception as e: print(f"Update Field Error: {e}")

def update_profile(row_num, key, value):
    sheet = get_db()
    if sheet:
        try:
            current_json = sheet.cell(row_num, COL_PROFILE).value
            data = json.loads(current_json) if current_json else {}
            data[key] = sanitize(value) if isinstance(value, str) else value
            sheet.update_cell(row_num, COL_PROFILE, json.dumps(data, ensure_ascii=False))
        except Exception as e: print(f"Update Profile Error: {e}")

def update_profile_batch(row_num, updates_dict):
    """Пакетное обновление профиля для экономии квоты API (Один запрос вместо нескольких)"""
    sheet = get_db()
    if sheet:
        try:
            current_json = sheet.cell(row_num, COL_PROFILE).value
            data = json.loads(current_json) if current_json else {}
            for k, v in updates_dict.items():
                data[k] = sanitize(v) if isinstance(v, str) else v
            sheet.update_cell(row_num, COL_PROFILE, json.dumps(data, ensure_ascii=False))
            return True
        except Exception as e:
            print(f"Batch Update Error: {e}")
    return False

def save_history(row_num, history_list):
    sheet = get_db()
    if sheet:
        try: sheet.update_cell(row_num, COL_HISTORY, json.dumps(history_list, ensure_ascii=False))
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
            
            r_num = idx + 1
            u_email = row[COL_EMAIL - 1]
            u_name = row[COL_NAME - 1]
            p_json = row[COL_PROFILE - 1] 
            users.append((r_num, u_email, u_name, p_json))
        return users
    except Exception as e:
        print(f"Get All Users Error: {e}")
        return []
