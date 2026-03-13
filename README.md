
# Beauty Salon Booking Platform (Frontend + Django Backend)

Production-oriented full-stack project for a modern beauty-salon booking workflow.

## Tech Stack

- Frontend reference UI: static HTML/CSS/JS in `Frontend/`
- Backend: Python 3.x + Django
- Database: PostgreSQL
- Production serving: Gunicorn + Nginx
- Containerization: Docker + docker-compose
- File storage: local persistent media volume (`/app/media`)

## Project Structure

```text
Frontend/
  index.html
  salons.html
  salon_detail.html
  register.html
  login.html
  profile.html
  booking.html
  css/
  js/

backend/
  manage.py
  config/
  accounts/
  salons/
  bookings/
  templates/
  static/
  nginx/
  requirements.txt
  Dockerfile
  entrypoint.sh

docker-compose.yml
.env.example
```

## Environment Variables

Copy `.env.example` to `.env` and adjust values:

```env
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_USE_SQLITE=False

POSTGRES_DB=beauty_salon
POSTGRES_USER=beauty_user
POSTGRES_PASSWORD=beauty_password
POSTGRES_HOST=db
POSTGRES_PORT=5432
```

## Local Setup (Without Docker)

1. Create virtual environment and install dependencies:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

1. Set environment variables (or use a local `.env` loader).

For quick local testing without PostgreSQL, set:

```env
DJANGO_USE_SQLITE=True
```

1. Run migrations:

```bash
python manage.py migrate
```

1. Create superuser:

```bash
python manage.py createsuperuser
```

1. Run development server:

```bash
python manage.py runserver
```

## Docker Deployment

1. Create `.env` from `.env.example`.

1. Build and run:

```bash
docker compose up --build
```

1. Access app at `http://localhost`.

1. Access admin at `http://localhost/admin/`.

### Persistence Notes

- Uploaded receipts are stored in `/app/media`.
- `docker-compose.yml` mounts `/app/media` to `media_data` volume.
- Do not remove this volume if you need to preserve uploaded files.

## Static and Media Configuration

Configured in `backend/config/settings.py`:

```python
STATIC_URL = "/static/"
STATIC_ROOT = "/app/staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = "/app/media"
```

## Core Endpoints

- `/register/`
- `/login/`
- `/login/2fa/`
- `/profile/`
- `/salons/`
- `/salon/<id>/`
- `/api/salon/<id>/availability/?date=YYYY-MM-DD`
- `/booking/create/`

## Admin Salon Management

Beauty salons are managed from Django Admin (`/admin/`).

Admin can manage per salon:

- salon name
- rating
- address
- structured working days and hours
- phone number
- email
- description
- services and prices
- 3-4 salon photos (enforced in admin inline validation)

### Load Sample Salon Data

After migrations, load sample salons/services/photos:

```bash
cd backend
python manage.py loaddata salons/fixtures/sample_salons.json
```

## Booking Rules

- Slot uniqueness is enforced by DB constraint on `(salon, booking_date, start_time)`.
- Booking creation uses transaction + row locking to prevent race conditions.
- Availability API reports slots and `fully_booked` for a date.

## Payment Upload Rules

- Allowed file types: `.jpg`, `.jpeg`, `.png`, `.pdf`
- Max size: `3MB`
- Validation happens both client-side and server-side.
- Files are stored under: `media/payments/<year>/<month>/<filename>`

## Running Tests

```bash
cd backend
export DJANGO_USE_SQLITE=True  # PowerShell: $env:DJANGO_USE_SQLITE="true"
python manage.py test
```

Included tests cover:

- booking uniqueness constraint
- fully booked day detection
- enabling/disabling 2FA
- login flow with 2FA

## API Examples

### cURL: Register

```bash
curl -X POST http://localhost/register/ \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","username":"demo","password":"StrongPass123"}'
```

### cURL: Availability

```bash
curl "http://localhost/api/salon/1/availability/?date=2026-03-16"
```

### JavaScript fetch: Login step 1

```javascript
const response = await fetch("/login/", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "X-CSRFToken": csrftoken,
  },
  credentials: "same-origin",
  body: JSON.stringify({ identifier: "demo", password: "StrongPass123" }),
});

const payload = await response.json();
if (payload.require_2fa) {
  // POST to /login/2fa/ with payload.token and secret word
}
```

## Notes

- `Frontend/` is the standalone UI reference implementation.
- Django templates in `backend/templates/` reuse the same page structures and static asset names.
  