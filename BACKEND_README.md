# E-Panchakarma Backend (Flask + MySQL)

This backend is implemented in `app.py` and includes:

- Patient and doctor authentication
- Session-token based authorization
- Dosha analysis and therapy recommendation storage
- Doctor recommendation engine
- Appointment booking and doctor dashboard APIs
- MySQL database/table bootstrap

## 1. Install Dependencies

```bash
pip install -r requirements.txt
```

## 2. Configure Environment

Copy `.env.example` values into your shell environment.

PowerShell example:

```powershell
$env:MYSQL_HOST="localhost"
$env:MYSQL_USER="root"
$env:MYSQL_PASSWORD="your_mysql_password"
$env:MYSQL_DATABASE="e_panchakarma"
$env:MYSQL_PORT="3306"
$env:GOOGLE_CLIENT_ID="your_google_web_client_id.apps.googleusercontent.com"
# Optional for production-hardening:
# $env:GOOGLE_AUDIENCE_STRICT="true"
```

## 3. Run Backend

```bash
python app.py
```

Server starts on:

- `http://127.0.0.1:5000`

## 4. Initialize Database (run once)

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:5000/init-db"
```

## 5. Health Checks

- `GET /health`
- `GET /db-check`

## API Summary

### Auth

- `POST /api/auth/patient/register`
- `POST /api/auth/patient/login`
- `POST /api/auth/google` (Google Sign-In via backend, requires `GOOGLE_CLIENT_ID`)
- `POST /api/auth/doctor/register`
- `POST /api/auth/doctor/login`
- `POST /api/auth/logout`

Notes for Google auth:
- Default behavior is audience-flexible for local/demo setup (`GOOGLE_AUDIENCE_STRICT=false`).
- To enforce strict audience matching in production, set `GOOGLE_AUDIENCE_STRICT=true` and provide valid `GOOGLE_CLIENT_ID` values.

### Doctors

- `GET /api/doctors`
- `GET /api/doctors/recommend`

### Analysis

- `POST /api/analysis` (patient auth required)
- `GET /api/analysis/latest` (patient auth required)

### Appointments

- `POST /api/appointments` (patient auth required)
- `GET /api/appointments/my` (patient auth required)
- `GET /api/doctor/appointments` (doctor auth required)
- `PATCH /api/doctor/appointments/<id>/status` (doctor auth required)
- `GET /api/doctor/dashboard` (doctor auth required)

### Profiles

- `GET /api/patient/profile` (patient auth required)
- `GET /api/doctor/profile` (doctor auth required)

## Authorization Header

After login/register, pass returned token in header:

```text
Authorization: Bearer <token>
```

## Quick Test Flow

1. `POST /init-db`
2. Register doctor
3. Register patient
4. Login patient and save token
5. Call `POST /api/analysis`
6. Call `GET /api/doctors/recommend`
7. Call `POST /api/appointments`
