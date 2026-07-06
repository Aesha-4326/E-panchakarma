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

If you do not want to type SMTP settings every time, create a local file named `.env.local` in the project root and copy the format from `.env.local.example`. The `start-backend.ps1` script will automatically read values from `.env.local`.

PowerShell example:

```powershell
$env:MYSQL_HOST="localhost"
$env:MYSQL_USER="root"
$env:MYSQL_PASSWORD="your_mysql_password"
$env:MYSQL_DATABASE="e_panchakarma"
$env:MYSQL_PORT="3307"
$env:SMTP_HOST="smtp.gmail.com"
$env:SMTP_PORT="587"
$env:SMTP_USERNAME="your_email@gmail.com"
$env:SMTP_PASSWORD="your_app_password"
$env:SMTP_FROM_EMAIL="your_email@gmail.com"
$env:SMTP_FROM_NAME="E-Panchakarma"
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
- `POST /api/auth/patient/request-otp`
- `POST /api/auth/patient/login-otp`
- `POST /api/auth/google` (Google Sign-In via backend, requires `GOOGLE_CLIENT_ID`)
- `POST /api/auth/doctor/register`
- `POST /api/auth/doctor/login`
- `POST /api/auth/doctor/request-otp`
- `POST /api/auth/doctor/login-otp`
- `POST /api/auth/logout`

Notes for Google auth:
- Default behavior is audience-flexible for local/demo setup (`GOOGLE_AUDIENCE_STRICT=false`).
- To enforce strict audience matching in production, set `GOOGLE_AUDIENCE_STRICT=true` and provide valid `GOOGLE_CLIENT_ID` values.

Notes for email OTP auth:
- OTP emails require SMTP settings (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`).
- Default OTP expiry is 10 minutes.
- Default resend cooldown is 60 seconds.

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
- `PATCH /api/doctor/appointments/<id>/reschedule` (doctor auth required)
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
4. Login patient with password or OTP and save token
5. Call `POST /api/analysis`
6. Call `GET /api/doctors/recommend`
7. Call `POST /api/appointments`
