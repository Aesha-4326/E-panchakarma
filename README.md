# E-Panchakarma

E-Panchakarma is a web-based Ayurvedic healthcare platform that helps patients explore Panchakarma therapies, complete symptom-based dosha analysis, receive therapy recommendations, and connect with doctors for appointments, prescriptions, and follow-up support.

## Description

web based Ayurvedic healthcare platform for dosha analysis, Panchakarma therapy guidance, doctor recommendations, and online appointments.`

## Project Overview

This project  is a full-stack web application that digitizes Ayurvedic Panchakarma healthcare services. The platform enables patients to perform symptom-based dosha analysis, receive Panchakarma therapy recommendations, book appointments with Ayurvedic doctors, and manage prescriptions through a secure online portal.

The system also provides doctors with tools to manage appointments, generate prescriptions, communicate with patients, and monitor treatment progress.


## Features

##Patients can:

- Register and log in with password, OTP, or Google Sign-In
- Patient Registration & Profile Management
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
- Create & Update prescriptions
- Chat with patients inside the system
- View dashboard summaries and notifications

## Admin Module

- Manage Patients
- Manage Doctors
- Monitor Appointments
- View System Reports
- Database Management

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

- Frontend: HTML5, CSS3, JavaScript(ES6), Bootstrap5, Chart.js, jsPDF, Firebase Auth
- Backend: Python, Flask, Flask-CORS, REST APIs
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
│
├── static/
│   ├── css/
│   ├── js/
│   └── images/
│
├── templates/
│
└── database/
    └── MySQL Tables
```

##  Installation

### Clone Repository

```bash
git clone https://github.com/Aesha-4326/E-Panchakarma.git
```

### Navigate to Project

```bash
cd E-Panchakarma
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure Database

* Create a MySQL database.
* Update database credentials in `app.py`.
* Import the required tables.

### Run the Application

```bash
python app.py
```

The application will start on:

```
http://localhost:5000
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

## Security Features

* OTP-Based Authentication
* Google OAuth Login
* Role-Based Access Control
* Input Validation
* Secure REST APIs
* Database Authentication
* Session Management

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

## Future Improvements

- Online Video Consultation
- Digital Payment Gateway
- Android & iOS Mobile Applications
- AI Chatbot for 24×7 Assistance
- Add automated tests for backend APIs
- Add file uploads and richer medical record support
- Add stronger validation and audit logging
- Advanced Health Analytics Dashboard

## Author

Aesha Narola
B.Tech Information Technology
github: https://github.com/Aesha-4326/E-panchakarma
