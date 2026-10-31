from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from PIL import Image, UnidentifiedImageError


def validate_review_image(image):
    if image.size > 5 * 1024 * 1024:
        raise ValidationError("Each review photo must be 5 MB or smaller.")
    image_file = getattr(image, "file", image)
    try:
        image_file.seek(0)
        with Image.open(image_file) as decoded_image:
            image_format = decoded_image.format
            width, height = decoded_image.size
            if image_format not in {"JPEG", "PNG", "WEBP"}:
                raise ValidationError("Review photos must be JPG, PNG, or WebP images.")
            if width * height > 20_000_000:
                raise ValidationError("Review photos must be no larger than 20 megapixels.")
            decoded_image.verify()
        image_file.seek(0)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise ValidationError("Review photos must be JPG, PNG, or WebP images.")


class CarMake(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class CarModel(models.Model):
    TYPES = [("SEDAN", "Sedan"), ("SUV", "SUV"), ("WAGON", "Wagon"), ("COUPE", "Coupe"), ("TRUCK", "Truck")]
    car_make = models.ForeignKey(CarMake, on_delete=models.CASCADE, related_name="models")
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=10, choices=TYPES, default="SEDAN")
    year = models.IntegerField(default=2023, validators=[MinValueValidator(2015), MaxValueValidator(2023)])

    def __str__(self):
        return f"{self.car_make.name} {self.name}"


class Dealer(models.Model):
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, db_index=True)
    st = models.CharField(max_length=2)
    address = models.CharField(max_length=200)
    zip = models.CharField(max_length=10)
    lat = models.FloatField()
    long = models.FloatField()
    short_name = models.CharField(max_length=100)
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=30, blank=True)
    website = models.URLField(blank=True)
    hours = models.TextField(blank=True)

    def __str__(self):
        return self.full_name


class Review(models.Model):
    STATUS_CHOICES = [("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")]
    dealership = models.ForeignKey(Dealer, on_delete=models.CASCADE, related_name="reviews")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="dealer_reviews")
    name = models.CharField(max_length=100)
    review = models.TextField()
    purchase = models.BooleanField(default=False)
    verified_purchase = models.BooleanField(default=False)
    rating = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    recommend = models.BooleanField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending", db_index=True)
    purchase_date = models.CharField(max_length=20, blank=True)
    car_make = models.CharField(max_length=100, blank=True)
    car_model = models.CharField(max_length=100, blank=True)
    car_year = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    def __str__(self):
        return f"{self.name} @ {self.dealership_id}"


class ReviewPhoto(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="review-photos/%Y/%m/", validators=[validate_review_image])
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    def __str__(self):
        return f"Photo for review {self.review_id}"


class HelpfulVote(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="helpful_votes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="helpful_review_votes")
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["review", "user"], name="unique_helpful_vote_per_user")]


class ReviewReport(models.Model):
    STATUS_CHOICES = [("open", "Open"), ("resolved", "Resolved"), ("dismissed", "Dismissed")]
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="review_reports")
    reason = models.CharField(max_length=500)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="open", db_index=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["review", "reporter"], name="unique_review_report_per_user")]


class DealerFavorite(models.Model):
    dealer = models.ForeignKey(Dealer, on_delete=models.CASCADE, related_name="favorites")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dealer_favorites")
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["dealer", "user"], name="unique_dealer_favorite_per_user")]


class DealerResponse(models.Model):
    review = models.OneToOneField(Review, on_delete=models.CASCADE, related_name="dealer_response")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="dealer_responses")
    response = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Response to review {self.review_id}"


class Car(models.Model):
    dealer = models.ForeignKey(Dealer, on_delete=models.CASCADE, related_name="cars")
    make = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    body_type = models.CharField(max_length=30, blank=True)
    year = models.IntegerField()
    mileage = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.year} {self.make} {self.model}"
