# Car Dealership Reviews (Django + SQL + React/Vite)

```bash
cd server && pip install -r requirements.txt
python manage.py migrate && python manage.py seed && python manage.py createsuperuser
python manage.py runserver        # app at :8000 (uses frontend/dist)
```
Optional: `cd frontend && npm install && npm run build` (or `npm run dev` with Django running).
Sentiment service: `cd djangoapp/microservices && pip install -r requirements.txt && flask run -p 5050` (falls back to "neutral" if offline).

For deployments, set `DJANGO_SECRET_KEY` to a private, randomly generated value; the fallback in Django settings is for local development only.

## Run with Docker

```bash
cd server
cp .env.example .env
# Replace DB_PASSWORD and DJANGO_SECRET_KEY with unique local values.
docker compose up --build
```

Docker builds the React frontend into the Django image, serves static assets with WhiteNoise, and runs Django and the sentiment service with Gunicorn. `DEBUG` is disabled in Compose. User uploads are stored separately from collected static assets in the persistent `media_data` volume. PostgreSQL health checks ensure the database is ready before migrations run. Keep `server/.env` private and use separate strong credentials for deployments.

## Dealership and review features

- The dealer directory supports state, city, vehicle make, and body-type filters, rating/review/name sorting, and server-side pagination.
- Dealer pages include average ratings, inventory, customer recommendations, sortable, paginated reviews, an OpenStreetMap location, directions, and optional phone, website, and hours.
- Signed-in users can save dealers, compare up to three in the current browser, mark reviews helpful once, report reviews, and submit reviews with up to three JPG, PNG, or WebP photos (5 MB each).
- New reviews are pending until an administrator or staff moderator approves them. Staff can also reject reviews, verify a purchase claim, resolve/dismiss reports, and post or update an official dealership response.

Use `/admin/` to manage dealerships and their optional phone, website, and hours fields. Staff accounts can use the in-app `/moderation` page. A purchase is only labeled verified after a moderator confirms it; checking the purchase box when writing a review does not verify it automatically.

Uploaded review photos use Django's `MEDIA_ROOT` and `MEDIA_URL` settings. Keep the media directory persistent and configure protected, appropriate media serving when deploying beyond local development. Map tiles and directions are provided by OpenStreetMap and require no API key.
