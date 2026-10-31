"""Load dealers, reviews and cars from the original Mongo JSON seed files into SQL."""
import json
from pathlib import Path

from django.core.management.base import BaseCommand

from djangoapp.models import Car, CarMake, CarModel, Dealer, Review

DATA = Path(__file__).resolve().parents[3] / "seed_data"


class Command(BaseCommand):
    def handle(self, *args, **opts):
        dealers = json.loads((DATA / "dealerships.json").read_text())["dealerships"]
        for d in dealers:
            Dealer.objects.update_or_create(id=d["id"], defaults={k: d[k] for k in
                ("city", "state", "st", "address", "zip", "lat", "long", "short_name", "full_name")})
        ids = set(Dealer.objects.values_list("id", flat=True))
        for r in json.loads((DATA / "reviews.json").read_text())["reviews"]:
            if r["dealership"] not in ids:
                continue
            Review.objects.update_or_create(id=r["id"], defaults=dict(
                dealership_id=r["dealership"], name=r["name"], review=r["review"],
                purchase=r["purchase"], purchase_date=r.get("purchase_date") or "",
                car_make=r.get("car_make") or "", car_model=r.get("car_model") or "",
                car_year=r.get("car_year")))
        for c in json.loads((DATA / "car_records.json").read_text())["cars"]:
            if c.get("dealer_id") in ids:
                Car.objects.get_or_create(dealer_id=c["dealer_id"], make=c["make"], model=c["model"], year=c["year"],
                    defaults={"body_type": c["bodyType"], "mileage": c.get("mileage", 0)})
            make, _ = CarMake.objects.get_or_create(name=c["make"])
            t = c["bodyType"].upper()
            CarModel.objects.get_or_create(car_make=make, name=c["model"], year=c["year"],
                defaults={"type": t if t in dict(CarModel.TYPES) else "SEDAN"})
        self.stdout.write(self.style.SUCCESS(
            f"{Dealer.objects.count()} dealers, {Review.objects.count()} reviews, {CarModel.objects.count()} car models"))
