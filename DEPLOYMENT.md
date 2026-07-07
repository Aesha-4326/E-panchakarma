# E-Panchakarma Deployment

This project is a Flask web app with MySQL. The Flask app serves both the frontend and backend:

- Frontend page: `/`
- Images: `/images/<filename>`
- APIs: `/api/...`

## Required Environment Variables

Set these on your hosting platform:

```env
MYSQL_HOST=your_mysql_host
MYSQL_USER=your_mysql_user
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=e_panchakarma
MYSQL_PORT=3307

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_gmail_app_password
SMTP_FROM_EMAIL=your_email@gmail.com
SMTP_FROM_NAME=E-Panchakarma
SMTP_USE_TLS=true
SMTP_USE_SSL=false

APP_DEBUG=false
GOOGLE_CLIENT_ID=
GOOGLE_AUDIENCE_STRICT=false
```

Railway MySQL may provide these variable names instead:

```env
MYSQLHOST=...
MYSQLUSER=...
MYSQLPASSWORD=...
MYSQLDATABASE=...
MYSQLPORT=...
```

The backend supports both naming styles. On a deployed web service, do not use `MYSQL_HOST=127.0.0.1` unless MySQL is running inside the same container.

## Render/Railway Style Settings

Use these values for a Python web service:

```text
Build command: pip install -r requirements.txt
Start command: gunicorn app:app
```

After deployment, open:

```text
https://your-domain/
```

Then initialize the database once:

```powershell
Invoke-RestMethod -Method Post -Uri "https://your-domain/init-db"
```

## Images

Images will appear after deployment because they are inside the project `images/` folder and referenced with relative paths such as:

```html
images/E-Panchakarma.jpg
images/Vamana_therapy.jpg
```
