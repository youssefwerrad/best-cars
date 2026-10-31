# Car Dealership Reviews

A full-stack dealership review app built with Django REST endpoints, SQLite or
PostgreSQL, and a React frontend bundled with Vite.

## Run locally

These steps run Django and serve the built React app from the same address.
Run commands from the repository root unless a step says otherwise.

### 1. Configure the environment

```bash
cd server
cp .env.example .env
```

Edit `server/.env` and set `DJANGO_SECRET_KEY` to a new, private value. You can
generate one after installing the Python requirements:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copy the printed value into `.env`. Do not commit `.env` or use a key that has
been shared publicly. SQLite is used by default; no database server is needed
for this local setup.

### 2. Install dependencies and build the frontend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd frontend
npm ci
npm run build
cd ..
```

### 3. Initialize and start Django

```bash
python manage.py migrate
python manage.py seed
python manage.py collectstatic --noinput
python manage.py runserver
```

Open <http://127.0.0.1:8000/>. The `collectstatic` step copies the Vite build
into Django's static files directory. Run it again after rebuilding the
frontend. If a browser reports that a stylesheet has MIME type `text/html`,
check that the CSS file exists under `server/staticfiles/assets/`, run
`collectstatic` again, and restart Django.

To create an administrator account for `/admin/`, run this in another terminal
with the virtual environment activated:

```bash
cd server
python manage.py createsuperuser
```

## Frontend development

To work on React without rebuilding for each change, keep Django running on
port 8000 and start Vite in another terminal:

```bash
cd server/frontend
npm run dev
```

Open the URL printed by Vite. Its development server proxies `/djangoapp`
requests to Django. Use the `runserver` workflow above when you want to test the
production-style build served by Django.

## Run with Docker Compose

From `server/`, copy the example environment file if you have not already,
replace the database password and Django secret with unique values, then start
the services:

```bash
cp .env.example .env
docker compose up --build
```

Open <http://127.0.0.1:8000/>. Compose starts PostgreSQL and the sentiment
service, applies migrations, loads seed data, builds the frontend, and serves
static assets through WhiteNoise. Uploaded photos persist in a separate volume
from static files.

Stop the containers with `Ctrl+C`. To remove the containers while keeping
database and uploaded-media volumes, run `docker compose down`.

## Optional sentiment service (without Docker)

The sentiment service is not required to run the app. If you want it locally,
install and start it in a separate terminal:

```bash
cd server/djangoapp/microservices
pip install -r requirements.txt
flask run -p 5050
```

If the service is unavailable when a review is submitted, the review is saved
without a sentiment value.

## Features

- Browse dealerships and filter inventory by location, make, and body type.
- View dealership details, ratings, inventory, customer recommendations, and
  paginated reviews.
- Sign in to save or compare dealerships, mark reviews helpful, report reviews,
  and submit reviews with photos.
- Staff moderators can approve or reject reviews, verify purchase claims,
  manage reports, and post dealership responses.
- Use Django Admin at `/admin/` to manage dealership data.

New reviews are pending until approved by an administrator or staff moderator.
A purchase is only labeled verified after a moderator confirms it.

## Deployment notes

Keep `DJANGO_SECRET_KEY` and database credentials private, and use unique,
strong values outside local development. Configure HTTPS and trusted proxy
settings before enabling secure redirects, HSTS, or secure cookies. Keep
uploaded media persistent and configure suitable media access for your
deployment; uploaded files are separate from collected static assets.
