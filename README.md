# E-Panchakarma

E-Panchakarma is a web-based Ayurvedic healthcare platform that helps patients explore Panchakarma therapies, complete symptom-based dosha analysis, receive therapy recommendations, and connect with doctors for appointments, prescriptions, and follow-up support.

## Short GitHub Description

Use this in the GitHub repository description field:

`AI-powered Ayurvedic healthcare platform for dosha analysis, Panchakarma therapy guidance, doctor recommendations, and online appointments.`

## Project Overview

This project combines a patient-facing frontend with a Flask + MySQL backend for a more complete digital Panchakarma workflow.

Patients can:

- Register and log in with password, OTP, or Google Sign-In
- Complete symptom-based dosha analysis
- View recommended Panchakarma therapies and lifestyle guidance
- Book appointments with recommended doctors
- Track appointment status and notifications
- View prescriptions and chat with doctors
- Download health or prescription-related summaries

Doctors can:

- Register and log in with password, OTP, or Google Sign-In
- Manage appointments and patient activity
- Update appointment status or reschedule visits
- Search patients by issue, dosha pattern, or profile details
- Create prescriptions
- Chat with patients inside the system
- View dashboard summaries and notifications

## Main Features

- Dosha analysis with therapy recommendation logic
- Panchakarma therapy information for Vamana, Virechana, Basti, Nasya, and Raktamokshana
- Doctor recommendation engine based on issue, dosha, and therapy match
- Patient and doctor authentication
- OTP email login support
- Google Sign-In support
- Appointment booking and management
- Prescription creation and patient access
- Doctor-patient chat per appointment
- Multilingual frontend content
- PDF export support on the frontend

## Tech Stack

- Frontend: HTML, CSS, JavaScript, Bootstrap, Chart.js, jsPDF, Firebase Auth
- Backend: Python, Flask, Flask-CORS
- Database: MySQL
- Auth/Integrations: Google Sign-In, SMTP email OTP

## Project Structure

```text
.
|-- e-panchakarma.html      # Main frontend application
|-- app.py                  # Flask backend
|-- requirements.txt        # Python dependencies
|-- BACKEND_README.md       # Backend-focused notes
|-- images/                 # Therapy and branding images
|-- api_examples.http       # Sample API requests
|-- start-backend.ps1       # Local backend startup script
|-- stop-backend.ps1        # Local backend shutdown script
|-- init-backend.ps1        # Backend initialization helper
```

## Frontend Highlights

The frontend includes:

- Patient login and registration pages
- Doctor login and registration pages
- Patient dashboard
- Symptom analysis flow
- Result page with dosha and therapy details
- Appointment booking page
- Panchakarma therapy guide pages
- Doctor admin dashboard
- Prescription and chat interfaces

The main frontend file is:

- `e-panchakarma.html`

## Backend Highlights

The backend is implemented in `app.py` and provides:

- Database bootstrap and connection helpers
- Patient and doctor authentication APIs
- OTP request and verification flows
- Google Sign-In verification
- Dosha analysis storage
- Doctor recommendation endpoints
- Appointment creation, listing, status update, and rescheduling
- Doctor dashboard and profile management
- Prescription APIs
- Patient-doctor chat APIs
- Notification endpoints

## Requirements

Before running the project, make sure you have:

- Python 3.10 or newer
- MySQL Server
- `pip`
- Internet access for CDN-hosted frontend libraries
- Optional: SMTP credentials for OTP emails
- Optional: Google client credentials for Google Sign-In

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Aesha-4326/E-panchakarma.git
cd E-panchakarma
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a local `.env.local` file in the project root and add values like these:

```env
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=e_panchakarma
MYSQL_PORT=3306
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_FROM_EMAIL=your_email@gmail.com
SMTP_FROM_NAME=E-Panchakarma
GOOGLE_CLIENT_ID=your_google_web_client_id.apps.googleusercontent.com
GOOGLE_AUDIENCE_STRICT=false
```

### 4. Start the backend

PowerShell:

```powershell
python app.py
```

Or use the helper script:

```powershell
.\start-backend.cmd
```

### 5. Initialize the database

After the server starts, run:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:5000/init-db"
```

### 6. Open the frontend

Open the Flask app URL in your browser:

```text
http://127.0.0.1:5000
```

This serves `e-panchakarma.html` and the `images/` folder together, so therapy images also load when the app is opened from another device.

## View On Another Device

To open the app from another phone or laptop on the same Wi-Fi, first find this computer's local network IP address.

On Windows PowerShell, run:

```powershell
ipconfig
```

Look for the `IPv4 Address` under your Wi-Fi adapter. It usually looks like `192.168.1.25` or `192.168.0.10`.

Then open this URL on the other device:

```text
http://YOUR_COMPUTER_IP:5000
```

Example:

```text
http://192.168.1.25:5000
```

Both devices must be connected to the same Wi-Fi network.

### Windows Firewall

If the app opens on this computer but not on another device, Windows Firewall may be blocking port `5000`.

Allow Python or port `5000` through Windows Firewall:

1. Open Windows Security.
2. Go to Firewall & network protection.
3. Click Allow an app through firewall.
4. Allow Python for Private networks.

If needed, create an inbound firewall rule for TCP port `5000` on Private networks.

## Default Local Backend URL

```text
http://127.0.0.1:5000
```

## Key API Endpoints

### Health

- `GET /health`
- `GET /db-check`
- `POST /init-db`

### Patient Authentication

- `POST /api/auth/patient/register`
- `POST /api/auth/patient/login`
- `POST /api/auth/patient/request-otp`
- `POST /api/auth/patient/login-otp`
- `POST /api/auth/google`

### Doctor Authentication

- `POST /api/auth/doctor/register`
- `POST /api/auth/doctor/login`
- `POST /api/auth/doctor/request-otp`
- `POST /api/auth/doctor/login-otp`
- `POST /api/auth/doctor/google`

### Shared Auth

- `POST /api/auth/logout`

### Doctors

- `GET /api/doctors`
- `GET /api/doctors/recommend`
- `GET /api/doctor/profile`
- `PATCH /api/doctor/profile`
- `GET /api/doctor/dashboard`
- `GET /api/doctor/patients`

### Analysis

- `POST /api/analysis`
- `GET /api/analysis/latest`

### Appointments

- `POST /api/appointments`
- `GET /api/appointments/my`
- `GET /api/doctor/appointments`
- `PATCH /api/doctor/appointments/<id>/status`
- `PATCH /api/doctor/appointments/<id>/reschedule`

### Prescriptions

- `GET /api/doctor/prescriptions`
- `POST /api/doctor/prescriptions`
- `GET /api/patient/prescriptions`

### Chat

- `GET /api/doctor/chat/<appointment_id>`
- `POST /api/doctor/chat/<appointment_id>`
- `GET /api/patient/chat/<appointment_id>`
- `POST /api/patient/chat/<appointment_id>`

### Notifications

- `GET /api/patient/notifications`
- `GET /api/doctor/notifications`

### Miscellaneous

- `GET /api/medicines/suggest`
- `GET /api/patient/profile`

## Authorization

After login or registration, send the session token in the request header:

```text
Authorization: Bearer <token>
```

## Sample User Flow

1. Start the backend.
2. Initialize the database.
3. Register a doctor account.
4. Register a patient account.
5. Log in as patient.
6. Complete symptom analysis.
7. Review the recommended dosha and therapy.
8. Book an appointment with the suggested doctor.
9. Log in as doctor to manage the appointment.
10. Create a prescription or continue communication through chat.

## Notes

- The frontend currently uses CDN resources for Bootstrap, Chart.js, jsPDF, and Firebase.
- Local files such as `.env.local`, logs, and MySQL runtime data should be handled carefully and are usually not ideal for public repositories.
- Before production deployment, review secrets, database storage, CORS settings, authentication flows, and frontend API configuration.

## Future Improvements

- Split frontend HTML, CSS, and JavaScript into separate modules
- Add role-based admin features
- Add automated tests for backend APIs
- Improve production deployment setup
- Add file uploads and richer medical record support
- Add stronger validation and audit logging
