from __future__ import annotations

from datetime import date, datetime, time, timedelta
from email.message import EmailMessage
import json
import os
import secrets
import smtplib
from typing import Any
from urllib.parse import urlparse

from flask import Flask, g, jsonify, request, send_from_directory
from flask_cors import CORS
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
import mysql.connector
from mysql.connector import Error
from werkzeug.security import check_password_hash, generate_password_hash


def load_local_env_file(file_name: str = ".env.local") -> None:
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), file_name)
    if not os.path.exists(env_path):
        return

    with open(env_path, "r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if (
                len(value) >= 2
                and ((value[0] == value[-1] == '"') or (value[0] == value[-1] == "'"))
            ):
                value = value[1:-1]
            # .env.local should be the source of truth for local runs, even for blank values.
            os.environ[key] = value


load_local_env_file()


PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
CORS(app)


def env_first(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value is not None and value != "":
            return value
    return default


def database_config_from_url(database_url: str) -> dict[str, Any] | None:
    if not database_url:
        return None

    parsed = urlparse(database_url)
    if not parsed.hostname:
        return None

    return {
        "host": parsed.hostname,
        "user": parsed.username or "root",
        "password": parsed.password or "",
        "database": parsed.path.lstrip("/") or "e_panchakarma",
        "port": parsed.port or 3306,
    }


URL_DB_CONFIG = database_config_from_url(env_first("DATABASE_URL", "MYSQL_URL"))
DB_NAME = (
    URL_DB_CONFIG["database"]
    if URL_DB_CONFIG
    else env_first("MYSQL_DATABASE", "MYSQLDATABASE", default="e_panchakarma")
)
DB_CONFIG = {
    "host": env_first("MYSQL_HOST", "MYSQLHOST", default="localhost"),
    "user": env_first("MYSQL_USER", "MYSQLUSER", default="root"),
    "password": env_first("MYSQL_PASSWORD", "MYSQLPASSWORD", default=""),
    "database": DB_NAME,
    "port": int(env_first("MYSQL_PORT", "MYSQLPORT", default="3307")),
}
DB_SERVER_CONFIG = {
    "host": DB_CONFIG["host"],
    "user": DB_CONFIG["user"],
    "password": DB_CONFIG["password"],
    "port": DB_CONFIG["port"],
}
if URL_DB_CONFIG:
    DB_CONFIG.update(URL_DB_CONFIG)
    DB_SERVER_CONFIG.update(
        {
            "host": URL_DB_CONFIG["host"],
            "user": URL_DB_CONFIG["user"],
            "password": URL_DB_CONFIG["password"],
            "port": URL_DB_CONFIG["port"],
        }
    )
GOOGLE_CLIENT_IDS = [
    client_id.strip()
    for client_id in os.getenv("GOOGLE_CLIENT_ID", "").split(",")
    if client_id.strip()
]
STRICT_GOOGLE_AUDIENCE = os.getenv("GOOGLE_AUDIENCE_STRICT", "false").lower() in (
    "1",
    "true",
    "yes",
    "on",
)
SMTP_HOST = (os.getenv("SMTP_HOST") or "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = (os.getenv("SMTP_USERNAME") or "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes", "on")
SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "false").lower() in ("1", "true", "yes", "on")
SMTP_FROM_EMAIL = (
    os.getenv("SMTP_FROM_EMAIL")
    or SMTP_USERNAME
    or "no-reply@e-panchakarma.local"
).strip()
SMTP_FROM_NAME = (os.getenv("SMTP_FROM_NAME") or "E-Panchakarma").strip()
OTP_EXPIRY_MINUTES = int(os.getenv("OTP_EXPIRY_MINUTES", "10"))
OTP_RESEND_COOLDOWN_SECONDS = int(os.getenv("OTP_RESEND_COOLDOWN_SECONDS", "60"))
OTP_MAX_ATTEMPTS = int(os.getenv("OTP_MAX_ATTEMPTS", "5"))

SPECIALTIES = {
    "RESPIRATORY": "Respiratory & Kapha Care",
    "DIGESTIVE": "Digestive & Pitta Care",
    "VATA": "Vata & Pain Care",
    "ENT": "ENT & Head Care",
    "SKIN_BLOOD": "Skin & Blood Purification",
    "GENERAL": "General Panchakarma",
}

MEDICINE_SUGGESTIONS = [
    {"name": "Triphala Churna", "usage": "Digestive balance and gentle detox support"},
    {"name": "Ashwagandha", "usage": "Stress support and strength building"},
    {"name": "Brahmi", "usage": "Memory and calming support"},
    {"name": "Sitopaladi Churna", "usage": "Respiratory comfort support"},
    {"name": "Dashamoola Kwath", "usage": "Vata support and pain management"},
    {"name": "Avipattikar Churna", "usage": "Acidity and Pitta support"},
    {"name": "Neem Tablets", "usage": "Skin and blood purification support"},
    {"name": "Anu Taila", "usage": "Nasal care and ENT support"},
]

ISSUE_MAP = {
    "respiratory": {
        "specialty": SPECIALTIES["RESPIRATORY"],
        "reason": "Best fit for respiratory and Kapha complaints",
    },
    "digestive": {
        "specialty": SPECIALTIES["DIGESTIVE"],
        "reason": "Best fit for digestion and Pitta complaints",
    },
    "joint": {
        "specialty": SPECIALTIES["VATA"],
        "reason": "Best fit for joint pain and Vata complaints",
    },
    "sinus": {
        "specialty": SPECIALTIES["ENT"],
        "reason": "Best fit for sinus and head-region complaints",
    },
    "skin": {
        "specialty": SPECIALTIES["SKIN_BLOOD"],
        "reason": "Best fit for skin concerns",
    },
    "blood": {
        "specialty": SPECIALTIES["SKIN_BLOOD"],
        "reason": "Best fit for blood purification concerns",
    },
    "general": {
        "specialty": SPECIALTIES["GENERAL"],
        "reason": "Suitable for general Panchakarma guidance",
    },
}


def normalize_email(value: str) -> str:
    return (value or "").strip().lower()


def hash_value(value: str) -> str:
    return generate_password_hash(value)


def check_hash(hashed_value: str, plain_value: str) -> bool:
    return check_password_hash(hashed_value, plain_value)


def get_server_connection():
    return mysql.connector.connect(**DB_SERVER_CONFIG)


def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


def serialize_db_value(value: Any):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, time):
        return value.strftime("%H:%M:%S")
    if isinstance(value, timedelta):
        total_seconds = int(value.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return value


def normalize_db_row(row: dict[str, Any] | None):
    if not row:
        return row
    return {key: serialize_db_value(value) for key, value in row.items()}


def fetch_one(query: str, params: tuple[Any, ...] = ()):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params)
        return normalize_db_row(cursor.fetchone())
    finally:
        cursor.close()
        conn.close()


def fetch_all(query: str, params: tuple[Any, ...] = ()):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [normalize_db_row(row) for row in rows]
    finally:
        cursor.close()
        conn.close()


def execute_write(query: str, params: tuple[Any, ...] = ()) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        conn.commit()
        return cursor.lastrowid
    finally:
        cursor.close()
        conn.close()


def init_db():
    server_conn = get_server_connection()
    server_cursor = server_conn.cursor()
    try:
        server_cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
    finally:
        server_cursor.close()
        server_conn.close()

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS patients (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(120) NOT NULL,
                email VARCHAR(120) NOT NULL UNIQUE,
                age INT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS doctors (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(120) NOT NULL,
                email VARCHAR(120) NOT NULL UNIQUE,
                hospital VARCHAR(160) NULL,
                specialty VARCHAR(120) NOT NULL DEFAULT 'General Panchakarma',
                experience_years INT NULL,
                available_timings VARCHAR(255) NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        try:
            cursor.execute("ALTER TABLE doctors ADD COLUMN experience_years INT NULL")
        except Error:
            pass
        try:
            cursor.execute("ALTER TABLE doctors ADD COLUMN available_timings VARCHAR(255) NULL")
        except Error:
            pass

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                token VARCHAR(128) NOT NULL UNIQUE,
                user_type ENUM('patient','doctor') NOT NULL,
                user_id INT NOT NULL,
                expires_at DATETIME NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_token (token),
                INDEX idx_user (user_type, user_id)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS login_otps (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_type ENUM('patient','doctor') NOT NULL,
                user_id INT NOT NULL,
                email VARCHAR(120) NOT NULL,
                otp_hash VARCHAR(255) NOT NULL,
                expires_at DATETIME NOT NULL,
                consumed_at DATETIME NULL,
                attempts INT NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_otp_lookup (user_type, email, created_at),
                INDEX idx_otp_expiry (expires_at)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS symptom_reports (
                id INT AUTO_INCREMENT PRIMARY KEY,
                patient_id INT NOT NULL,
                vata_count INT NOT NULL DEFAULT 0,
                pitta_count INT NOT NULL DEFAULT 0,
                kapha_count INT NOT NULL DEFAULT 0,
                vata_symptoms TEXT,
                pitta_symptoms TEXT,
                kapha_symptoms TEXT,
                final_dosha VARCHAR(40) NOT NULL,
                therapy VARCHAR(200) NOT NULL,
                diet TEXT,
                therapy_description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_symptom_patient FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS appointments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                patient_id INT NOT NULL,
                doctor_id INT NOT NULL,
                issue VARCHAR(120) NOT NULL,
                dosha VARCHAR(40) DEFAULT 'Not analyzed',
                therapy VARCHAR(200) DEFAULT 'Not assigned',
                progress VARCHAR(60) DEFAULT 'Not Started',
                appointment_date DATE NOT NULL,
                appointment_time TIME NOT NULL,
                status VARCHAR(40) DEFAULT 'Pending',
                suggested_by_system TINYINT(1) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                CONSTRAINT fk_appointment_patient FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
                CONSTRAINT fk_appointment_doctor FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS prescriptions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                appointment_id INT NOT NULL,
                doctor_id INT NOT NULL,
                patient_id INT NOT NULL,
                medicines TEXT NOT NULL,
                notes TEXT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_prescription_appointment FOREIGN KEY (appointment_id) REFERENCES appointments(id) ON DELETE CASCADE,
                CONSTRAINT fk_prescription_doctor FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE CASCADE,
                CONSTRAINT fk_prescription_patient FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                appointment_id INT NOT NULL,
                doctor_id INT NOT NULL,
                patient_id INT NOT NULL,
                sender_type ENUM('doctor','patient') NOT NULL,
                message_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_chat_appointment FOREIGN KEY (appointment_id) REFERENCES appointments(id) ON DELETE CASCADE,
                CONSTRAINT fk_chat_doctor FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE CASCADE,
                CONSTRAINT fk_chat_patient FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
            )
            """
        )

        conn.commit()
    finally:
        cursor.close()
        conn.close()


def create_session(user_type: str, user_id: int) -> dict[str, Any]:
    token = secrets.token_urlsafe(40)
    expires_at = datetime.utcnow() + timedelta(days=7)
    execute_write(
        """
        INSERT INTO user_sessions (token, user_type, user_id, expires_at)
        VALUES (%s, %s, %s, %s)
        """,
        (token, user_type, user_id, expires_at),
    )
    return {
        "token": token,
        "expires_at": expires_at.isoformat() + "Z",
        "user_type": user_type,
        "user_id": user_id,
    }


def parse_datetime_value(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return None
    return None


def smtp_is_configured() -> bool:
    return bool(SMTP_HOST and SMTP_FROM_EMAIL)


def send_email(recipient_email: str, subject: str, body: str) -> None:
    if not smtp_is_configured():
        raise RuntimeError(
            "Email OTP is not configured on backend. Set SMTP_HOST, SMTP_PORT, SMTP_USERNAME, "
            "SMTP_PASSWORD and SMTP_FROM_EMAIL in your environment."
        )

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
    message["To"] = recipient_email
    message.set_content(body)

    if SMTP_USE_SSL:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=20) as server:
            if SMTP_USERNAME:
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(message)
        return

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
        server.ehlo()
        if SMTP_USE_TLS:
            server.starttls()
            server.ehlo()
        if SMTP_USERNAME:
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(message)


def get_user_record_by_email(user_type: str, email: str) -> dict[str, Any] | None:
    if user_type == "patient":
        return fetch_one(
            "SELECT id, name, email, age, password_hash FROM patients WHERE email = %s",
            (email,),
        )
    return fetch_one(
        """
        SELECT id, name, email, hospital, specialty, experience_years, available_timings, password_hash
        FROM doctors
        WHERE email = %s
        """,
        (email,),
    )


def build_login_response(user_type: str, user: dict[str, Any], message: str):
    session_data = create_session(user_type, user["id"])
    if user_type == "patient":
        return jsonify(
            {
                "message": message,
                "patient": {
                    "id": user["id"],
                    "name": user["name"],
                    "email": user["email"],
                    "age": user["age"],
                },
                "session": session_data,
            }
        )
    return jsonify(
        {
            "message": message,
            "doctor": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "hospital": user["hospital"],
                "specialty": user["specialty"],
                "experience_years": user.get("experience_years"),
                "available_timings": user.get("available_timings"),
            },
            "session": session_data,
        }
    )


def generate_otp_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def request_login_otp(user_type: str):
    data = request.get_json(silent=True) or {}
    email = normalize_email(data.get("email", ""))

    if not email:
        return jsonify({"error": "email is required"}), 400

    user = get_user_record_by_email(user_type, email)
    if not user:
        return jsonify({"error": f"{user_type} account not found for this email"}), 404

    latest_otp = fetch_one(
        """
        SELECT id, created_at
        FROM login_otps
        WHERE user_type = %s AND email = %s AND consumed_at IS NULL
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (user_type, email),
    )
    created_at = parse_datetime_value(latest_otp["created_at"]) if latest_otp else None
    if created_at and created_at > datetime.utcnow() - timedelta(seconds=OTP_RESEND_COOLDOWN_SECONDS):
        return jsonify(
            {
                "error": f"Please wait {OTP_RESEND_COOLDOWN_SECONDS} seconds before requesting a new OTP"
            }
        ), 429

    execute_write(
        """
        UPDATE login_otps
        SET consumed_at = %s
        WHERE user_type = %s AND email = %s AND consumed_at IS NULL
        """,
        (datetime.utcnow(), user_type, email),
    )

    otp_code = generate_otp_code()
    expires_at = datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)
    execute_write(
        """
        INSERT INTO login_otps (user_type, user_id, email, otp_hash, expires_at)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (user_type, user["id"], email, hash_value(otp_code), expires_at),
    )

    subject = f"{SMTP_FROM_NAME} login OTP"
    body = (
        f"Hello {user['name']},\n\n"
        f"Your one-time password for {user_type} login is: {otp_code}\n\n"
        f"This OTP will expire in {OTP_EXPIRY_MINUTES} minutes.\n"
        "If you did not request this code, you can ignore this email.\n"
    )
    try:
        send_email(email, subject, body)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    return jsonify(
        {
            "message": f"OTP sent to {email}",
            "expires_in_minutes": OTP_EXPIRY_MINUTES,
        }
    )


def verify_login_otp(user_type: str):
    data = request.get_json(silent=True) or {}
    email = normalize_email(data.get("email", ""))
    otp = (data.get("otp") or "").strip()

    if not email or not otp:
        return jsonify({"error": "email and otp are required"}), 400

    user = get_user_record_by_email(user_type, email)
    if not user:
        return jsonify({"error": f"{user_type} account not found for this email"}), 404

    otp_record = fetch_one(
        """
        SELECT id, otp_hash, expires_at, attempts
        FROM login_otps
        WHERE user_type = %s AND email = %s AND consumed_at IS NULL
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (user_type, email),
    )
    if not otp_record:
        return jsonify({"error": "No active OTP found. Request a new OTP first"}), 400

    expires_at = parse_datetime_value(otp_record["expires_at"])
    if not expires_at or expires_at < datetime.utcnow():
        execute_write("UPDATE login_otps SET consumed_at = %s WHERE id = %s", (datetime.utcnow(), otp_record["id"]))
        return jsonify({"error": "OTP expired. Request a new OTP"}), 400

    if int(otp_record.get("attempts") or 0) >= OTP_MAX_ATTEMPTS:
        execute_write("UPDATE login_otps SET consumed_at = %s WHERE id = %s", (datetime.utcnow(), otp_record["id"]))
        return jsonify({"error": "OTP attempt limit reached. Request a new OTP"}), 400

    if not check_hash(otp_record["otp_hash"], otp):
        execute_write(
            "UPDATE login_otps SET attempts = attempts + 1 WHERE id = %s",
            (otp_record["id"],),
        )
        return jsonify({"error": "Invalid OTP"}), 401

    execute_write(
        "UPDATE login_otps SET consumed_at = %s WHERE id = %s",
        (datetime.utcnow(), otp_record["id"]),
    )
    return build_login_response(user_type, user, f"{user_type.title()} OTP login successful")


def verify_google_sign_in(id_token_value: str) -> dict[str, Any]:
    if STRICT_GOOGLE_AUDIENCE and not GOOGLE_CLIENT_IDS:
        raise ValueError(
            "Google login is not configured on backend. Set GOOGLE_CLIENT_ID environment variable."
        )

    try:
        # Validate token signature and basic claims using Google public certs.
        token_info = google_id_token.verify_oauth2_token(
            id_token_value,
            google_requests.Request(),
            audience=None,
        )
    except Exception as exc:
        raise ValueError(f"Invalid Google token: {exc}") from exc

    audience = token_info.get("aud")
    if STRICT_GOOGLE_AUDIENCE and audience not in GOOGLE_CLIENT_IDS:
        raise ValueError("Google token audience does not match backend configuration.")

    issuer = token_info.get("iss")
    if issuer not in ("accounts.google.com", "https://accounts.google.com"):
        raise ValueError("Google token issuer is invalid.")

    if not token_info.get("email_verified"):
        raise ValueError("Google account email is not verified.")

    return token_info


def extract_bearer_token() -> str | None:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    return auth_header.replace("Bearer ", "", 1).strip()


def require_auth(user_type: str):
    token = extract_bearer_token()
    if not token:
        return None, (jsonify({"error": "Authorization token missing"}), 401)

    session = fetch_one(
        """
        SELECT id, user_type, user_id, expires_at
        FROM user_sessions
        WHERE token = %s
        """,
        (token,),
    )
    if not session:
        return None, (jsonify({"error": "Invalid token"}), 401)

    if session["user_type"] != user_type:
        return None, (jsonify({"error": "Access denied for this token type"}), 403)

    expires_at = parse_datetime_value(session["expires_at"])
    if expires_at and expires_at < datetime.utcnow():
        execute_write("DELETE FROM user_sessions WHERE id = %s", (session["id"],))
        return None, (jsonify({"error": "Token expired"}), 401)

    g.current_user = {"id": session["user_id"], "type": session["user_type"]}
    return g.current_user, None


def get_therapy_plan(dosha: str) -> dict[str, str]:
    if dosha == "Vata":
        return {
            "therapy": "Basti Therapy (Medicated Enema)",
            "diet": "Warm meals, grounding routine, oil massage, and timely sleep",
            "description": "Basti supports Vata balance and helps with dryness, irregular digestion, and stiffness.",
        }
    if dosha == "Pitta":
        return {
            "therapy": "Virechana Therapy (Purgation)",
            "diet": "Cooling food, hydration, avoid very spicy and deep-fried meals",
            "description": "Virechana helps reduce excessive Pitta and heat-related digestive or skin complaints.",
        }
    return {
        "therapy": "Vamana Therapy (Therapeutic Emesis)",
        "diet": "Light meals, regular movement, less oily and heavy foods",
        "description": "Vamana is often used for Kapha excess linked with congestion, heaviness, and sluggishness.",
    }


def analyze_dosha(vata_count: int, pitta_count: int, kapha_count: int) -> str:
    dosha = "Kapha"
    if vata_count > pitta_count and vata_count > kapha_count:
        dosha = "Vata"
    elif pitta_count > vata_count and pitta_count > kapha_count:
        dosha = "Pitta"
    return dosha


def parse_iso_date(value: Any) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def build_patient_notifications(patient_id: int) -> list[dict[str, Any]]:
    appointments = fetch_all(
        """
        SELECT a.id, a.issue, a.status, a.appointment_date, a.appointment_time, a.created_at,
               d.name AS doctor_name, d.specialty AS doctor_specialty
        FROM appointments a
        JOIN doctors d ON d.id = a.doctor_id
        WHERE a.patient_id = %s
        ORDER BY a.appointment_date ASC, a.appointment_time ASC
        """,
        (patient_id,),
    )
    today = date.today()
    notifications: list[dict[str, Any]] = []

    for appointment in appointments:
        appointment_day = parse_iso_date(appointment.get("appointment_date"))
        if not appointment_day:
            continue
        day_diff = (appointment_day - today).days
        status = appointment.get("status") or "Pending"
        doctor_name = appointment.get("doctor_name") or "your doctor"

        if status in {"Pending", "Confirmed"} and 0 <= day_diff <= 1:
            notifications.append(
                {
                    "type": "appointment_reminder",
                    "priority": 1,
                    "title": "Appointment reminder",
                    "message": f"You have an appointment with Dr. {doctor_name} on {appointment['appointment_date']} at {appointment['appointment_time']}.",
                }
            )

        if status in {"Confirmed", "Completed"} and appointment_day < today:
            notifications.append(
                {
                    "type": "follow_up",
                    "priority": 2,
                    "title": "Follow-up alert",
                    "message": f"Follow up with Dr. {doctor_name} for your {appointment.get('issue') or 'consultation'} visit.",
                }
            )

    notifications.sort(key=lambda item: item["priority"])
    return notifications[:6]


def build_doctor_notifications(doctor_id: int) -> list[dict[str, Any]]:
    appointments = fetch_all(
        """
        SELECT a.id, a.issue, a.status, a.appointment_date, a.appointment_time, a.created_at,
               p.name AS patient_name
        FROM appointments a
        JOIN patients p ON p.id = a.patient_id
        WHERE a.doctor_id = %s
        ORDER BY a.created_at DESC, a.appointment_date ASC, a.appointment_time ASC
        """,
        (doctor_id,),
    )
    today = date.today()
    notifications: list[dict[str, Any]] = []

    for appointment in appointments:
        appointment_day = parse_iso_date(appointment.get("appointment_date"))
        if not appointment_day:
            continue
        day_diff = (appointment_day - today).days
        status = appointment.get("status") or "Pending"
        patient_name = appointment.get("patient_name") or "Patient"

        if status == "Pending":
            notifications.append(
                {
                    "type": "new_patient_request",
                    "priority": 1,
                    "title": "New patient request",
                    "message": f"{patient_name} requested an appointment for {appointment.get('issue') or 'consultation'}.",
                }
            )

        if status in {"Pending", "Confirmed"} and 0 <= day_diff <= 1:
            notifications.append(
                {
                    "type": "appointment_reminder",
                    "priority": 2,
                    "title": "Appointment reminder",
                    "message": f"You have an appointment with {patient_name} on {appointment['appointment_date']} at {appointment['appointment_time']}.",
                }
            )

        if status in {"Confirmed", "Completed"} and appointment_day < today:
            notifications.append(
                {
                    "type": "follow_up",
                    "priority": 3,
                    "title": "Follow-up alert",
                    "message": f"Check in with {patient_name} after the {appointment.get('issue') or 'consultation'} visit.",
                }
            )

    notifications.sort(key=lambda item: item["priority"])
    return notifications[:8]


def doctor_match_meta(specialty: str, issue: str, dosha: str, therapy: str) -> tuple[int, str]:
    score = 1 if specialty == SPECIALTIES["GENERAL"] else 0
    reason = "General Panchakarma support"
    issue_data = ISSUE_MAP.get((issue or "").lower())

    if issue_data and specialty == issue_data["specialty"]:
        score += 4
        reason = issue_data["reason"]

    if dosha == "Kapha" and specialty == SPECIALTIES["RESPIRATORY"]:
        score += 3
        reason = "Matches Kapha imbalance and respiratory support"
    if dosha == "Pitta" and specialty == SPECIALTIES["DIGESTIVE"]:
        score += 3
        reason = "Matches Pitta imbalance and digestive detox support"
    if dosha == "Vata" and specialty == SPECIALTIES["VATA"]:
        score += 3
        reason = "Matches Vata imbalance and pain management support"

    if "Nasya" in therapy and specialty == SPECIALTIES["ENT"]:
        score += 3
        reason = "Matches Nasya-related ENT and head care"
    if "Rakta" in therapy and specialty == SPECIALTIES["SKIN_BLOOD"]:
        score += 3
        reason = "Matches blood purification and skin care"
    if "Vamana" in therapy and specialty == SPECIALTIES["RESPIRATORY"]:
        score += 3
        reason = "Matches Vamana support for Kapha and respiratory detox"
    if "Virechana" in therapy and specialty == SPECIALTIES["DIGESTIVE"]:
        score += 3
        reason = "Matches Virechana support for digestive and Pitta detox"
    if "Basti" in therapy and specialty == SPECIALTIES["VATA"]:
        score += 3
        reason = "Matches Basti support for Vata and pain management"

    return score, reason


def get_ranked_doctors(issue: str, dosha: str, therapy: str) -> list[dict[str, Any]]:
    doctors = fetch_all(
        """
        SELECT id, name, email, hospital, specialty, created_at
        FROM doctors
        ORDER BY created_at DESC
        """
    )
    ranked = []
    for doctor in doctors:
        score, reason = doctor_match_meta(doctor["specialty"], issue, dosha, therapy)
        ranked.append(
            {
                "doctor": doctor,
                "score": score,
                "reason": reason,
            }
        )
    ranked.sort(key=lambda x: (-x["score"], x["doctor"]["name"].lower()))
    return ranked


@app.get("/")
def home():
    return send_from_directory(PROJECT_ROOT, "e-panchakarma.html")


@app.get("/images/<path:filename>")
def frontend_image(filename: str):
    return send_from_directory(os.path.join(PROJECT_ROOT, "images"), filename)


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/db-check")
def db_check():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DATABASE()")
        current_db = cursor.fetchone()[0]
        return jsonify({"connected": True, "database": current_db})
    except Error as exc:
        return jsonify({"connected": False, "error": str(exc)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


@app.post("/init-db")
def init_db_route():
    try:
        init_db()
        return jsonify({"message": "Database and tables ready"})
    except Error as exc:
        return jsonify({"error": str(exc)}), 500


@app.post("/api/auth/patient/register")
def patient_register():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = normalize_email(data.get("email", ""))
    age = data.get("age")

    if not name or not email:
        return jsonify({"error": "name and email are required"}), 400

    existing = fetch_one("SELECT id FROM patients WHERE email = %s", (email,))
    if existing:
        return jsonify({"error": "patient email already registered"}), 409

    patient_id = execute_write(
        """
        INSERT INTO patients (name, email, age, password_hash)
        VALUES (%s, %s, %s, %s)
        """,
        (name, email, age, generate_password_hash(secrets.token_urlsafe(32))),
    )
    session_data = create_session("patient", patient_id)
    return jsonify({"message": "Patient registered", "patient_id": patient_id, "session": session_data}), 201


@app.post("/api/auth/patient/login")
def patient_login():
    data = request.get_json(silent=True) or {}
    email = normalize_email(data.get("email", ""))
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    patient = get_user_record_by_email("patient", email)
    if not patient or not check_password_hash(patient["password_hash"], password):
        return jsonify({"error": "invalid credentials"}), 401

    return build_login_response("patient", patient, "Patient login successful")


@app.post("/api/auth/patient/request-otp")
def patient_request_otp():
    return request_login_otp("patient")


@app.post("/api/auth/patient/login-otp")
def patient_login_otp():
    return verify_login_otp("patient")


@app.post("/api/auth/google")
def patient_google_login():
    data = request.get_json(silent=True) or {}
    id_token_value = data.get("id_token", "")

    if not id_token_value:
        return jsonify({"error": "id_token is required"}), 400

    try:
        token_info = verify_google_sign_in(id_token_value)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 401

    email = normalize_email(token_info.get("email", ""))
    if not email:
        return jsonify({"error": "Google account did not provide an email"}), 400

    display_name = (token_info.get("name") or "").strip() or "Google User"
    picture = token_info.get("picture", "")

    patient = fetch_one(
        "SELECT id, name, email, age FROM patients WHERE email = %s",
        (email,),
    )
    if not patient:
        patient_id = execute_write(
            """
            INSERT INTO patients (name, email, age, password_hash)
            VALUES (%s, %s, %s, %s)
            """,
            (display_name, email, None, generate_password_hash(secrets.token_urlsafe(32))),
        )
        patient = fetch_one(
            "SELECT id, name, email, age FROM patients WHERE id = %s",
            (patient_id,),
        )

    session_data = create_session("patient", patient["id"])
    return jsonify(
        {
            "message": "Google login successful",
            "patient": {
                "id": patient["id"],
                "name": patient["name"],
                "email": patient["email"],
                "age": patient["age"],
                "picture": picture,
            },
            "session": session_data,
        }
    )


@app.post("/api/auth/doctor/google")
def doctor_google_login():
    data = request.get_json(silent=True) or {}
    id_token_value = data.get("id_token", "")

    if not id_token_value:
        return jsonify({"error": "id_token is required"}), 400

    try:
        token_info = verify_google_sign_in(id_token_value)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 401

    email = normalize_email(token_info.get("email", ""))
    if not email:
        return jsonify({"error": "Google account did not provide an email"}), 400

    display_name = (token_info.get("name") or "").strip() or "Google Doctor"
    picture = token_info.get("picture", "")

    doctor = fetch_one(
        "SELECT id, name, email, hospital, specialty, experience_years, available_timings FROM doctors WHERE email = %s",
        (email,),
    )
    if not doctor:
        doctor_id = execute_write(
            """
            INSERT INTO doctors (name, email, hospital, specialty, experience_years, available_timings, password_hash)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                display_name,
                email,
                "",
                SPECIALTIES["GENERAL"],
                None,
                "",
                generate_password_hash(secrets.token_urlsafe(32)),
            ),
        )
        doctor = fetch_one(
            "SELECT id, name, email, hospital, specialty, experience_years, available_timings FROM doctors WHERE id = %s",
            (doctor_id,),
        )

    session_data = create_session("doctor", doctor["id"])
    return jsonify(
        {
            "message": "Doctor Google login successful",
            "doctor": {
                "id": doctor["id"],
                "name": doctor["name"],
                "email": doctor["email"],
                "hospital": doctor["hospital"],
                "specialty": doctor["specialty"],
                "experience_years": doctor.get("experience_years"),
                "available_timings": doctor.get("available_timings"),
                "picture": picture,
            },
            "session": session_data,
        }
    )


@app.post("/api/auth/doctor/register")
def doctor_register():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = normalize_email(data.get("email", ""))
    hospital = (data.get("hospital") or "").strip()
    specialty = (data.get("specialty") or SPECIALTIES["GENERAL"]).strip()
    experience_years = data.get("experience_years")
    available_timings = (data.get("available_timings") or "").strip()

    if not name or not email:
        return jsonify({"error": "name and email are required"}), 400

    existing = fetch_one("SELECT id FROM doctors WHERE email = %s", (email,))
    if existing:
        return jsonify({"error": "doctor email already registered"}), 409

    doctor_id = execute_write(
        """
        INSERT INTO doctors (name, email, hospital, specialty, experience_years, available_timings, password_hash)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (name, email, hospital, specialty, experience_years, available_timings, generate_password_hash(secrets.token_urlsafe(32))),
    )
    session_data = create_session("doctor", doctor_id)
    return jsonify({"message": "Doctor registered", "doctor_id": doctor_id, "session": session_data}), 201


@app.post("/api/auth/doctor/login")
def doctor_login():
    data = request.get_json(silent=True) or {}
    email = normalize_email(data.get("email", ""))
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    doctor = get_user_record_by_email("doctor", email)
    if not doctor or not check_password_hash(doctor["password_hash"], password):
        return jsonify({"error": "invalid credentials"}), 401

    return build_login_response("doctor", doctor, "Doctor login successful")


@app.post("/api/auth/doctor/request-otp")
def doctor_request_otp():
    return request_login_otp("doctor")


@app.post("/api/auth/doctor/login-otp")
def doctor_login_otp():
    return verify_login_otp("doctor")


@app.post("/api/auth/logout")
def logout():
    token = extract_bearer_token()
    if not token:
        return jsonify({"error": "Authorization token missing"}), 401
    execute_write("DELETE FROM user_sessions WHERE token = %s", (token,))
    return jsonify({"message": "Logged out"})


@app.get("/api/doctors")
def list_doctors():
    issue = (request.args.get("issue") or "").strip().lower()
    dosha = (request.args.get("dosha") or "").strip()
    therapy = (request.args.get("therapy") or "").strip()

    if issue or dosha or therapy:
        ranked = get_ranked_doctors(issue, dosha, therapy)
        return jsonify(
            [
                {
                    "id": item["doctor"]["id"],
                    "name": item["doctor"]["name"],
                    "email": item["doctor"]["email"],
                    "hospital": item["doctor"]["hospital"],
                    "specialty": item["doctor"]["specialty"],
                    "score": item["score"],
                    "reason": item["reason"],
                }
                for item in ranked
            ]
        )

    doctors = fetch_all(
        "SELECT id, name, email, hospital, specialty, created_at FROM doctors ORDER BY created_at DESC"
    )
    return jsonify(doctors)


@app.get("/api/doctors/recommend")
def recommend_doctor():
    issue = (request.args.get("issue") or "").strip().lower()
    dosha = (request.args.get("dosha") or "").strip()
    therapy = (request.args.get("therapy") or "").strip()
    ranked = get_ranked_doctors(issue, dosha, therapy)

    if not ranked:
        return jsonify({"recommended_doctor": None, "top_matches": []})

    return jsonify(
        {
            "recommended_doctor": {
                "id": ranked[0]["doctor"]["id"],
                "name": ranked[0]["doctor"]["name"],
                "email": ranked[0]["doctor"]["email"],
                "hospital": ranked[0]["doctor"]["hospital"],
                "specialty": ranked[0]["doctor"]["specialty"],
                "score": ranked[0]["score"],
                "reason": ranked[0]["reason"],
            },
            "top_matches": [
                {
                    "id": item["doctor"]["id"],
                    "name": item["doctor"]["name"],
                    "email": item["doctor"]["email"],
                    "hospital": item["doctor"]["hospital"],
                    "specialty": item["doctor"]["specialty"],
                    "score": item["score"],
                    "reason": item["reason"],
                }
                for item in ranked[:3]
            ],
        }
    )


@app.post("/api/analysis")
def create_analysis():
    user, auth_error = require_auth("patient")
    if auth_error:
        return auth_error

    data = request.get_json(silent=True) or {}
    vata_symptoms = data.get("vata_symptoms") or []
    pitta_symptoms = data.get("pitta_symptoms") or []
    kapha_symptoms = data.get("kapha_symptoms") or []

    if not isinstance(vata_symptoms, list) or not isinstance(pitta_symptoms, list) or not isinstance(kapha_symptoms, list):
        return jsonify({"error": "vata_symptoms, pitta_symptoms, kapha_symptoms must be arrays"}), 400

    vata_count = len(vata_symptoms)
    pitta_count = len(pitta_symptoms)
    kapha_count = len(kapha_symptoms)

    dosha = analyze_dosha(vata_count, pitta_count, kapha_count)
    plan = get_therapy_plan(dosha)

    report_id = execute_write(
        """
        INSERT INTO symptom_reports (
            patient_id, vata_count, pitta_count, kapha_count,
            vata_symptoms, pitta_symptoms, kapha_symptoms,
            final_dosha, therapy, diet, therapy_description
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            user["id"],
            vata_count,
            pitta_count,
            kapha_count,
            json.dumps(vata_symptoms),
            json.dumps(pitta_symptoms),
            json.dumps(kapha_symptoms),
            dosha,
            plan["therapy"],
            plan["diet"],
            plan["description"],
        ),
    )

    return jsonify(
        {
            "message": "Analysis completed",
            "report_id": report_id,
            "result": {
                "vata_count": vata_count,
                "pitta_count": pitta_count,
                "kapha_count": kapha_count,
                "final_dosha": dosha,
                "therapy": plan["therapy"],
                "diet": plan["diet"],
                "therapy_description": plan["description"],
            },
        }
    ), 201


@app.get("/api/analysis/latest")
def latest_analysis():
    user, auth_error = require_auth("patient")
    if auth_error:
        return auth_error

    report = fetch_one(
        """
        SELECT id, patient_id, vata_count, pitta_count, kapha_count,
               vata_symptoms, pitta_symptoms, kapha_symptoms,
               final_dosha, therapy, diet, therapy_description, created_at
        FROM symptom_reports
        WHERE patient_id = %s
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (user["id"],),
    )
    if not report:
        return jsonify({"message": "No analysis found", "report": None})

    for key in ("vata_symptoms", "pitta_symptoms", "kapha_symptoms"):
        report[key] = json.loads(report[key] or "[]")
    return jsonify(report)


@app.post("/api/appointments")
def create_appointment():
    user, auth_error = require_auth("patient")
    if auth_error:
        return auth_error

    data = request.get_json(silent=True) or {}
    issue = (data.get("issue") or "").strip().lower()
    doctor_id = data.get("doctor_id")
    appointment_date = data.get("appointment_date")
    appointment_time = data.get("appointment_time")
    use_system_suggestion = bool(data.get("use_system_suggestion", False))

    if not issue or not appointment_date or not appointment_time:
        return jsonify({"error": "issue, appointment_date and appointment_time are required"}), 400

    latest_report = fetch_one(
        """
        SELECT final_dosha, therapy
        FROM symptom_reports
        WHERE patient_id = %s
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (user["id"],),
    )
    dosha = latest_report["final_dosha"] if latest_report else "Not analyzed"
    therapy = latest_report["therapy"] if latest_report else "Not assigned"

    suggested_by_system = 0
    if doctor_id is None or use_system_suggestion:
        ranked = get_ranked_doctors(issue, dosha, therapy)
        if not ranked:
            return jsonify({"error": "No doctor registered yet"}), 400
        doctor_id = ranked[0]["doctor"]["id"]
        suggested_by_system = 1
    else:
        doctor_exists = fetch_one("SELECT id FROM doctors WHERE id = %s", (doctor_id,))
        if not doctor_exists:
            return jsonify({"error": "Selected doctor not found"}), 404

    appointment_id = execute_write(
        """
        INSERT INTO appointments (
            patient_id, doctor_id, issue, dosha, therapy, appointment_date, appointment_time, suggested_by_system
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (user["id"], doctor_id, issue, dosha, therapy, appointment_date, appointment_time, suggested_by_system),
    )

    return jsonify(
        {
            "message": "Appointment booked",
            "appointment_id": appointment_id,
            "doctor_id": doctor_id,
            "suggested_by_system": bool(suggested_by_system),
        }
    ), 201


@app.get("/api/appointments/my")
def my_appointments():
    user, auth_error = require_auth("patient")
    if auth_error:
        return auth_error

    appointments = fetch_all(
        """
        SELECT a.id, a.issue, a.dosha, a.therapy, a.progress, a.appointment_date, a.appointment_time,
               a.status, a.suggested_by_system, a.created_at,
               d.id AS doctor_id, d.name AS doctor_name, d.email AS doctor_email, d.specialty AS doctor_specialty
        FROM appointments a
        JOIN doctors d ON d.id = a.doctor_id
        WHERE a.patient_id = %s
        ORDER BY a.appointment_date DESC, a.appointment_time DESC
        """,
        (user["id"],),
    )
    return jsonify(appointments)


@app.get("/api/patient/notifications")
def patient_notifications():
    user, auth_error = require_auth("patient")
    if auth_error:
        return auth_error
    return jsonify(build_patient_notifications(user["id"]))


@app.get("/api/doctor/appointments")
def doctor_appointments():
    user, auth_error = require_auth("doctor")
    if auth_error:
        return auth_error

    appointments = fetch_all(
        """
        SELECT a.id, a.issue, a.dosha, a.therapy, a.progress, a.appointment_date, a.appointment_time,
               a.status, a.suggested_by_system, a.created_at,
               p.id AS patient_id, p.name AS patient_name, p.email AS patient_email, p.age AS patient_age
        FROM appointments a
        JOIN patients p ON p.id = a.patient_id
        WHERE a.doctor_id = %s
        ORDER BY a.appointment_date DESC, a.appointment_time DESC
        """,
        (user["id"],),
    )
    return jsonify(appointments)


@app.get("/api/doctor/notifications")
def doctor_notifications():
    user, auth_error = require_auth("doctor")
    if auth_error:
        return auth_error
    return jsonify(build_doctor_notifications(user["id"]))


@app.get("/api/doctor/patients")
def doctor_patients():
    user, auth_error = require_auth("doctor")
    if auth_error:
        return auth_error

    search = (request.args.get("search") or "").strip().lower()
    params: list[Any] = [user["id"]]
    where_search = ""
    if search:
        where_search = """
            AND (
                LOWER(p.name) LIKE %s
                OR LOWER(p.email) LIKE %s
                OR LOWER(COALESCE(a.issue, '')) LIKE %s
                OR LOWER(COALESCE(sr.final_dosha, '')) LIKE %s
            )
        """
        like_value = f"%{search}%"
        params.extend([like_value, like_value, like_value, like_value])

    patients = fetch_all(
        f"""
        SELECT
            p.id,
            p.name,
            p.email,
            p.age,
            MAX(a.appointment_date) AS last_appointment_date,
            COUNT(a.id) AS total_appointments,
            MAX(COALESCE(a.issue, '')) AS latest_issue,
            MAX(COALESCE(sr.final_dosha, '')) AS latest_dosha,
            MAX(COALESCE(sr.therapy, '')) AS latest_therapy
        FROM patients p
        JOIN appointments a ON a.patient_id = p.id
        LEFT JOIN symptom_reports sr ON sr.patient_id = p.id
        WHERE a.doctor_id = %s
        {where_search}
        GROUP BY p.id, p.name, p.email, p.age
        ORDER BY last_appointment_date DESC, p.name ASC
        """,
        tuple(params),
    )
    return jsonify(patients)


@app.patch("/api/doctor/appointments/<int:appointment_id>/status")
def update_appointment_status(appointment_id: int):
    user, auth_error = require_auth("doctor")
    if auth_error:
        return auth_error

    data = request.get_json(silent=True) or {}
    status = (data.get("status") or "").strip()
    valid_statuses = {"Pending", "Confirmed", "Completed", "Cancelled"}
    if status not in valid_statuses:
        return jsonify({"error": f"status must be one of: {', '.join(sorted(valid_statuses))}"}), 400

    appointment = fetch_one(
        "SELECT id FROM appointments WHERE id = %s AND doctor_id = %s",
        (appointment_id, user["id"]),
    )
    if not appointment:
        return jsonify({"error": "Appointment not found for this doctor"}), 404

    execute_write("UPDATE appointments SET status = %s WHERE id = %s", (status, appointment_id))
    return jsonify({"message": "Appointment status updated", "appointment_id": appointment_id, "status": status})


@app.patch("/api/doctor/appointments/<int:appointment_id>/reschedule")
def reschedule_appointment(appointment_id: int):
    user, auth_error = require_auth("doctor")
    if auth_error:
        return auth_error

    data = request.get_json(silent=True) or {}
    appointment_date = data.get("appointment_date")
    appointment_time = data.get("appointment_time")
    if not appointment_date or not appointment_time:
        return jsonify({"error": "appointment_date and appointment_time are required"}), 400

    appointment = fetch_one(
        "SELECT id FROM appointments WHERE id = %s AND doctor_id = %s",
        (appointment_id, user["id"]),
    )
    if not appointment:
        return jsonify({"error": "Appointment not found for this doctor"}), 404

    execute_write(
        "UPDATE appointments SET appointment_date = %s, appointment_time = %s, status = %s WHERE id = %s",
        (appointment_date, appointment_time, "Confirmed", appointment_id),
    )
    return jsonify(
        {
            "message": "Appointment rescheduled",
            "appointment_id": appointment_id,
            "appointment_date": appointment_date,
            "appointment_time": appointment_time,
        }
    )


@app.get("/api/doctor/dashboard")
def doctor_dashboard():
    user, auth_error = require_auth("doctor")
    if auth_error:
        return auth_error

    doctor = fetch_one(
        "SELECT id, name, email, hospital, specialty, experience_years, available_timings, created_at FROM doctors WHERE id = %s",
        (user["id"],),
    )
    latest_appointment = fetch_one(
        """
        SELECT a.id, a.issue, a.dosha, a.therapy, a.progress, a.status, a.appointment_date, a.appointment_time,
               p.name AS patient_name
        FROM appointments a
        JOIN patients p ON p.id = a.patient_id
        WHERE a.doctor_id = %s
        ORDER BY a.created_at DESC
        LIMIT 1
        """,
        (user["id"],),
    )
    total_appointments = fetch_one(
        "SELECT COUNT(*) AS total FROM appointments WHERE doctor_id = %s",
        (user["id"],),
    )
    pending_appointments = fetch_one(
        "SELECT COUNT(*) AS pending FROM appointments WHERE doctor_id = %s AND status = 'Pending'",
        (user["id"],),
    )
    total_patients = fetch_one(
        """
        SELECT COUNT(DISTINCT patient_id) AS total
        FROM appointments
        WHERE doctor_id = %s
        """,
        (user["id"],),
    )
    today_appointments = fetch_one(
        """
        SELECT COUNT(*) AS total
        FROM appointments
        WHERE doctor_id = %s AND appointment_date = CURDATE()
        """,
        (user["id"],),
    )
    status_breakdown = fetch_all(
        """
        SELECT status, COUNT(*) AS total
        FROM appointments
        WHERE doctor_id = %s
        GROUP BY status
        ORDER BY status ASC
        """,
        (user["id"],),
    )

    return jsonify(
        {
            "doctor": doctor,
            "stats": {
                "total_patients": total_patients["total"] if total_patients else 0,
                "total_appointments": total_appointments["total"] if total_appointments else 0,
                "today_appointments": today_appointments["total"] if today_appointments else 0,
                "pending_appointments": pending_appointments["pending"] if pending_appointments else 0,
            },
            "latest_appointment": latest_appointment,
            "status_breakdown": status_breakdown,
        }
    )


@app.get("/api/patient/profile")
def patient_profile():
    user, auth_error = require_auth("patient")
    if auth_error:
        return auth_error

    patient = fetch_one(
        "SELECT id, name, email, age, created_at FROM patients WHERE id = %s",
        (user["id"],),
    )
    return jsonify(patient)


@app.get("/api/doctor/profile")
def doctor_profile():
    user, auth_error = require_auth("doctor")
    if auth_error:
        return auth_error

    doctor = fetch_one(
        "SELECT id, name, email, hospital, specialty, experience_years, available_timings, created_at FROM doctors WHERE id = %s",
        (user["id"],),
    )
    return jsonify(doctor)


@app.patch("/api/doctor/profile")
def update_doctor_profile():
    user, auth_error = require_auth("doctor")
    if auth_error:
        return auth_error

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    hospital = (data.get("hospital") or "").strip()
    specialty = (data.get("specialty") or "").strip()
    experience_years = data.get("experience_years")
    available_timings = (data.get("available_timings") or "").strip()

    if not name or not specialty:
        return jsonify({"error": "name and specialty are required"}), 400

    execute_write(
        """
        UPDATE doctors
        SET name = %s, hospital = %s, specialty = %s, experience_years = %s, available_timings = %s
        WHERE id = %s
        """,
        (name, hospital, specialty, experience_years, available_timings, user["id"]),
    )
    doctor = fetch_one(
        "SELECT id, name, email, hospital, specialty, experience_years, available_timings, created_at FROM doctors WHERE id = %s",
        (user["id"],),
    )
    return jsonify({"message": "Doctor profile updated", "doctor": doctor})


@app.get("/api/medicines/suggest")
def medicine_suggestions():
    query = (request.args.get("q") or "").strip().lower()
    if not query:
        return jsonify(MEDICINE_SUGGESTIONS)
    return jsonify(
        [
            item
            for item in MEDICINE_SUGGESTIONS
            if query in item["name"].lower() or query in item["usage"].lower()
        ]
    )


@app.get("/api/doctor/prescriptions")
def doctor_prescriptions():
    user, auth_error = require_auth("doctor")
    if auth_error:
        return auth_error

    prescriptions = fetch_all(
        """
        SELECT pr.id, pr.appointment_id, pr.medicines, pr.notes, pr.created_at,
               p.name AS patient_name
        FROM prescriptions pr
        JOIN patients p ON p.id = pr.patient_id
        WHERE pr.doctor_id = %s
        ORDER BY pr.created_at DESC
        """,
        (user["id"],),
    )
    for prescription in prescriptions:
        prescription["medicines"] = json.loads(prescription["medicines"] or "[]")
    return jsonify(prescriptions)


@app.post("/api/doctor/prescriptions")
def create_prescription():
    user, auth_error = require_auth("doctor")
    if auth_error:
        return auth_error

    data = request.get_json(silent=True) or {}
    appointment_id = data.get("appointment_id")
    medicines = data.get("medicines") or []
    notes = (data.get("notes") or "").strip()

    if not appointment_id or not isinstance(medicines, list) or not medicines:
        return jsonify({"error": "appointment_id and medicines are required"}), 400

    appointment = fetch_one(
        "SELECT id, patient_id FROM appointments WHERE id = %s AND doctor_id = %s",
        (appointment_id, user["id"]),
    )
    if not appointment:
        return jsonify({"error": "Appointment not found for this doctor"}), 404

    prescription_id = execute_write(
        """
        INSERT INTO prescriptions (appointment_id, doctor_id, patient_id, medicines, notes)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (appointment_id, user["id"], appointment["patient_id"], json.dumps(medicines), notes),
    )
    return jsonify({"message": "Prescription created", "prescription_id": prescription_id}), 201


@app.get("/api/patient/prescriptions")
def patient_prescriptions():
    user, auth_error = require_auth("patient")
    if auth_error:
        return auth_error

    prescriptions = fetch_all(
        """
        SELECT pr.id, pr.appointment_id, pr.medicines, pr.notes, pr.created_at,
               d.name AS doctor_name
        FROM prescriptions pr
        JOIN doctors d ON d.id = pr.doctor_id
        WHERE pr.patient_id = %s
        ORDER BY pr.created_at DESC
        """,
        (user["id"],),
    )
    for prescription in prescriptions:
        prescription["medicines"] = json.loads(prescription["medicines"] or "[]")
    return jsonify(prescriptions)


@app.get("/api/doctor/chat/<int:appointment_id>")
def doctor_chat_messages(appointment_id: int):
    user, auth_error = require_auth("doctor")
    if auth_error:
        return auth_error

    appointment = fetch_one(
        "SELECT id FROM appointments WHERE id = %s AND doctor_id = %s",
        (appointment_id, user["id"]),
    )
    if not appointment:
        return jsonify({"error": "Appointment not found for this doctor"}), 404

    messages = fetch_all(
        """
        SELECT id, sender_type, message_text, created_at
        FROM chat_messages
        WHERE appointment_id = %s
        ORDER BY created_at ASC
        """,
        (appointment_id,),
    )
    return jsonify(messages)


@app.post("/api/doctor/chat/<int:appointment_id>")
def doctor_send_chat_message(appointment_id: int):
    user, auth_error = require_auth("doctor")
    if auth_error:
        return auth_error

    data = request.get_json(silent=True) or {}
    message_text = (data.get("message_text") or "").strip()
    if not message_text:
        return jsonify({"error": "message_text is required"}), 400

    appointment = fetch_one(
        "SELECT id, patient_id FROM appointments WHERE id = %s AND doctor_id = %s",
        (appointment_id, user["id"]),
    )
    if not appointment:
        return jsonify({"error": "Appointment not found for this doctor"}), 404

    message_id = execute_write(
        """
        INSERT INTO chat_messages (appointment_id, doctor_id, patient_id, sender_type, message_text)
        VALUES (%s, %s, %s, 'doctor', %s)
        """,
        (appointment_id, user["id"], appointment["patient_id"], message_text),
    )
    return jsonify({"message": "Chat message sent", "message_id": message_id}), 201


@app.get("/api/patient/chat/<int:appointment_id>")
def patient_chat_messages(appointment_id: int):
    user, auth_error = require_auth("patient")
    if auth_error:
        return auth_error

    appointment = fetch_one(
        "SELECT id FROM appointments WHERE id = %s AND patient_id = %s",
        (appointment_id, user["id"]),
    )
    if not appointment:
        return jsonify({"error": "Appointment not found for this patient"}), 404

    messages = fetch_all(
        """
        SELECT id, sender_type, message_text, created_at
        FROM chat_messages
        WHERE appointment_id = %s
        ORDER BY created_at ASC
        """,
        (appointment_id,),
    )
    return jsonify(messages)


@app.post("/api/patient/chat/<int:appointment_id>")
def patient_send_chat_message(appointment_id: int):
    user, auth_error = require_auth("patient")
    if auth_error:
        return auth_error

    data = request.get_json(silent=True) or {}
    message_text = (data.get("message_text") or "").strip()
    if not message_text:
        return jsonify({"error": "message_text is required"}), 400

    appointment = fetch_one(
        "SELECT id, doctor_id FROM appointments WHERE id = %s AND patient_id = %s",
        (appointment_id, user["id"]),
    )
    if not appointment:
        return jsonify({"error": "Appointment not found for this patient"}), 404

    message_id = execute_write(
        """
        INSERT INTO chat_messages (appointment_id, doctor_id, patient_id, sender_type, message_text)
        VALUES (%s, %s, %s, 'patient', %s)
        """,
        (appointment_id, appointment["doctor_id"], user["id"], message_text),
    )
    return jsonify({"message": "Chat message sent", "message_id": message_id}), 201


@app.errorhandler(404)
def not_found(_err):
    return jsonify({"error": "Route not found"}), 404


@app.errorhandler(500)
def internal_error(_err):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    debug_enabled = os.getenv("APP_DEBUG", "false").lower() in ("1", "true", "yes", "on")
    app.run(host="0.0.0.0", port=5000, debug=debug_enabled, use_reloader=debug_enabled)
