import json

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator, EmptyPage
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, F, Q
from django.forms.models import model_to_dict
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import (Car, CarModel, Dealer, DealerFavorite, DealerResponse,
                     HelpfulVote, Review, ReviewPhoto, ReviewReport)
from .restapis import analyze_review_sentiments


def _dealer(d):
    data = model_to_dict(d) | {
        "id": d.id,
        "review_count": getattr(d, "review_count", 0) or 0,
        "average_rating": round(d.average_rating, 1) if getattr(d, "average_rating", None) is not None else None,
        "inventory_count": getattr(d, "inventory_count", 0) or 0,
    }
    if hasattr(d, "is_favorite"):
        data["is_favorite"] = d.is_favorite
    return data


def _json_body(request):
    if request.content_type == "application/json":
        try:
            return json.loads(request.body or b"{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None
    return request.POST


def _staff_required(request):
    return request.user.is_authenticated and request.user.is_staff


def _query_int(value, default, minimum, maximum):
    try:
        return min(max(int(value), minimum), maximum)
    except (TypeError, ValueError):
        return default


@csrf_exempt
def login_user(request):
    data = json.loads(request.body)
    user = authenticate(username=data["userName"], password=data["password"])
    if user is None:
        return JsonResponse({"userName": data["userName"]})
    login(request, user)
    return JsonResponse({"userName": user.username, "status": "Authenticated", "isStaff": user.is_staff})


def logout_user(request):
    logout(request)
    return JsonResponse({"userName": ""})


@csrf_exempt
def registration(request):
    data = json.loads(request.body)
    try:
        user = User.objects.create_user(
            username=data["userName"], password=data["password"],
            first_name=data.get("firstName", ""), last_name=data.get("lastName", ""),
            email=data.get("email", ""))
    except IntegrityError:
        return JsonResponse({"userName": data["userName"], "error": "Already Registered"})
    login(request, user)
    return JsonResponse({"userName": user.username, "status": "Authenticated"})


def get_cars(request):
    cars = CarModel.objects.select_related("car_make")
    return JsonResponse({"CarModels": [{"CarModel": c.name, "CarMake": c.car_make.name} for c in cars]})


def get_dealerships(request, state="All"):
    qs = Dealer.objects.annotate(
        review_count=Count("reviews", filter=Q(reviews__status="approved"), distinct=True),
        average_rating=Avg("reviews__rating", filter=Q(reviews__status="approved")),
        inventory_count=Count("cars", distinct=True),
    )
    if state != "All":
        qs = qs.filter(state__iexact=state)
    params = request.GET
    if params.get("state"):
        qs = qs.filter(state__iexact=params["state"])
    if params.get("q"):
        qs = qs.filter(Q(full_name__icontains=params["q"]) | Q(city__icontains=params["q"]))
    if params.get("city"):
        qs = qs.filter(city__icontains=params["city"])
    if params.get("make"):
        qs = qs.filter(cars__make__iexact=params["make"])
    if params.get("body_type"):
        qs = qs.filter(cars__body_type__iexact=params["body_type"])
    qs = qs.distinct()
    sort_options = {
        "rating": (F("average_rating").desc(nulls_last=True), "-review_count", "full_name"),
        "reviews": ("-review_count", "full_name"),
        "name": ("full_name",),
        "name_desc": ("-full_name",),
    }
    qs = qs.order_by(*sort_options.get(params.get("sort"), ("full_name",)))
    if request.user.is_authenticated:
        favorite_ids = set(DealerFavorite.objects.filter(user=request.user).values_list("dealer_id", flat=True))
    else:
        favorite_ids = set()
    paginator = Paginator(qs, _query_int(params.get("page_size"), 9, 1, 50))
    try:
        page = paginator.page(_query_int(params.get("page"), 1, 1, 1_000_000))
    except EmptyPage:
        page = paginator.page(paginator.num_pages or 1)
    dealers = []
    for dealer in page.object_list:
        dealer.is_favorite = dealer.id in favorite_ids
        dealers.append(_dealer(dealer))
    return JsonResponse({
        "status": 200, "dealers": dealers, "total": paginator.count,
        "page": page.number, "pages": paginator.num_pages,
        "states": list(Dealer.objects.order_by("state").values_list("state", flat=True).distinct()),
        "makes": list(Car.objects.order_by("make").values_list("make", flat=True).distinct()),
        "body_types": list(Car.objects.exclude(body_type="").order_by("body_type").values_list("body_type", flat=True).distinct()),
    })


def get_dealer_details(request, dealer_id):
    qs = Dealer.objects.annotate(
        review_count=Count("reviews", filter=Q(reviews__status="approved"), distinct=True),
        average_rating=Avg("reviews__rating", filter=Q(reviews__status="approved")),
        inventory_count=Count("cars", distinct=True),
    ).filter(id=dealer_id)
    dealer = qs.first()
    if dealer is None:
        return JsonResponse({"status": 404, "message": "Dealer not found"})
    dealer.is_favorite = request.user.is_authenticated and DealerFavorite.objects.filter(user=request.user, dealer=dealer).exists()
    return JsonResponse({"status": 200, "dealer": [_dealer(dealer)]})


def get_dealer_reviews(request, dealer_id):
    out = []
    reviews = Review.objects.filter(dealership_id=dealer_id, status="approved").annotate(
        helpful_count=Count("helpful_votes", distinct=True)
    ).select_related("dealer_response").prefetch_related("photos").order_by("-created_at")
    sort = request.GET.get("sort")
    if sort == "helpful":
        reviews = reviews.order_by("-helpful_count", "-created_at")
    elif sort == "rating":
        reviews = reviews.order_by("-rating", "-created_at")
    elif sort == "oldest":
        reviews = reviews.order_by("created_at")
    paginator = Paginator(reviews, _query_int(request.GET.get("page_size"), 6, 1, 24))
    try:
        page = paginator.page(_query_int(request.GET.get("page"), 1, 1, 1_000_000))
    except EmptyPage:
        page = paginator.page(paginator.num_pages or 1)
    for r in page.object_list:
        item = model_to_dict(r) | {
            "id": r.id, "dealership": r.dealership_id,
            "helpful_count": r.helpful_count,
            "helpful_by_me": request.user.is_authenticated and r.helpful_votes.filter(user=request.user).exists(),
            "photos": [photo.image.url for photo in r.photos.all()],
            "response": {
                "text": r.dealer_response.response,
                "author": r.dealer_response.author.username if r.dealer_response.author else "Dealership",
                "created_at": r.dealer_response.created_at.isoformat(),
            } if hasattr(r, "dealer_response") else None,
        }
        item["sentiment"] = analyze_review_sentiments(r.review)
        out.append(item)
    return JsonResponse({
        "status": 200, "reviews": out, "total": paginator.count,
        "page": page.number, "pages": paginator.num_pages,
    })


@csrf_exempt
def add_review(request):
    if request.method != "POST":
        return JsonResponse({"status": 405, "message": "POST required"}, status=405)
    if not request.user.is_authenticated:
        return JsonResponse({"status": 403, "message": "Unauthorized"}, status=403)
    d = _json_body(request)
    if d is None:
        return JsonResponse({"status": 400, "message": "Invalid request data"}, status=400)
    if not str(d.get("review", "")).strip():
        return JsonResponse({"status": 400, "message": "Review text is required"})
    try:
        rating = int(d.get("rating", ""))
    except (TypeError, ValueError):
        return JsonResponse({"status": 400, "message": "Choose a rating from 1 to 5."}, status=400)
    if rating < 1 or rating > 5:
        return JsonResponse({"status": 400, "message": "Choose a rating from 1 to 5."}, status=400)
    photos = request.FILES.getlist("photos")
    if len(photos) > 3:
        return JsonResponse({"status": 400, "message": "You can upload up to 3 photos."}, status=400)
    if any(photo.size > 5 * 1024 * 1024 for photo in photos):
        return JsonResponse({"status": 400, "message": "Each photo must be 5 MB or smaller."}, status=400)
    if len(str(d.get("review", "")).strip()) > 5000:
        return JsonResponse({"status": 400, "message": "Reviews must be 5,000 characters or fewer."}, status=400)
    recommend = d.get("recommend")
    if recommend not in (True, False, "true", "false", "yes", "no", "1", "0"):
        return JsonResponse({"status": 400, "message": "Choose whether you recommend this dealer."}, status=400)
    recommend = recommend in (True, "true", "yes", "1")
    try:
        with transaction.atomic():
            review = Review(
                dealership_id=int(d["dealership"]), author=request.user,
                name=request.user.username, review=str(d["review"]).strip(), rating=rating,
                recommend=recommend, purchase=str(d.get("purchase", "")).lower() in ("true", "1", "yes"),
                purchase_date=d.get("purchase_date", ""),
                car_make=d.get("car_make", ""), car_model=d.get("car_model", ""),
                car_year=d.get("car_year") or None)
            review.full_clean()
            review.save()
            review_photos = [ReviewPhoto(review=review, image=photo) for photo in photos]
            for review_photo in review_photos:
                review_photo.full_clean()
            for review_photo in review_photos:
                review_photo.save()
    except (ValueError, KeyError, Dealer.DoesNotExist):
        return JsonResponse({"status": 400, "message": "Choose a valid dealership."}, status=400)
    except ValidationError as error:
        return JsonResponse({"status": 400, "message": "; ".join(error.messages)}, status=400)
    except IntegrityError:
        return JsonResponse({"status": 400, "message": "Review could not be saved."}, status=400)
    return JsonResponse({
        "status": 200, "review_id": review.id,
        "message": "Review submitted for moderator approval.",
    })


def whoami(request):
    return JsonResponse({
        "userName": request.user.username if request.user.is_authenticated else "",
        "isStaff": bool(request.user.is_authenticated and request.user.is_staff),
    })


def get_dealer_cars(request, dealer_id):
    qs = Car.objects.filter(dealer_id=dealer_id).order_by("make", "model")
    return JsonResponse({"status": 200, "cars": list(qs.values("id", "make", "model", "body_type", "year", "mileage"))})


@csrf_exempt
def toggle_favorite(request, dealer_id):
    if request.method != "POST":
        return JsonResponse({"message": "POST required"}, status=405)
    if not request.user.is_authenticated:
        return JsonResponse({"message": "Sign in to save dealerships."}, status=403)
    if not Dealer.objects.filter(id=dealer_id).exists():
        return JsonResponse({"message": "Dealership not found."}, status=404)
    data = _json_body(request) or {}
    favorite = data.get("favorite")
    if favorite is True:
        DealerFavorite.objects.get_or_create(dealer_id=dealer_id, user=request.user)
    elif favorite is False:
        DealerFavorite.objects.filter(dealer_id=dealer_id, user=request.user).delete()
    else:
        return JsonResponse({"message": "A favorite state is required."}, status=400)
    return JsonResponse({"is_favorite": favorite})


def saved_dealers(request):
    if not request.user.is_authenticated:
        return JsonResponse({"message": "Sign in to view saved dealerships."}, status=403)
    qs = Dealer.objects.filter(favorites__user=request.user).annotate(
        review_count=Count("reviews", filter=Q(reviews__status="approved"), distinct=True),
        average_rating=Avg("reviews__rating", filter=Q(reviews__status="approved")),
        inventory_count=Count("cars", distinct=True),
    )
    dealers = []
    for dealer in qs.order_by("full_name"):
        dealer.is_favorite = True
        dealers.append(_dealer(dealer))
    return JsonResponse({"dealers": dealers})


@csrf_exempt
def helpful_vote(request, review_id):
    if request.method != "POST":
        return JsonResponse({"message": "POST required."}, status=405)
    if not request.user.is_authenticated:
        return JsonResponse({"message": "Sign in to mark reviews helpful."}, status=403)
    review = Review.objects.filter(id=review_id, status="approved").first()
    if review is None:
        return JsonResponse({"message": "Review not found."}, status=404)
    _, created = HelpfulVote.objects.get_or_create(review=review, user=request.user)
    return JsonResponse({
        "helpful": True, "created": created,
        "helpful_count": review.helpful_votes.count(),
    }, status=201 if created else 200)


@csrf_exempt
def report_review(request, review_id):
    if request.method != "POST":
        return JsonResponse({"message": "POST required."}, status=405)
    if not request.user.is_authenticated:
        return JsonResponse({"message": "Sign in to report a review."}, status=403)
    review = Review.objects.filter(id=review_id, status="approved").first()
    if review is None:
        return JsonResponse({"message": "Review not found."}, status=404)
    data = _json_body(request) or {}
    reason = str(data.get("reason", "")).strip()
    if not reason or len(reason) > 500:
        return JsonResponse({"message": "Provide a reason of 1 to 500 characters."}, status=400)
    try:
        with transaction.atomic():
            ReviewReport.objects.create(review=review, reporter=request.user, reason=reason)
    except IntegrityError:
        return JsonResponse({"message": "You have already reported this review."}, status=409)
    return JsonResponse({"message": "Report sent to moderators."}, status=201)


def moderation_queue(request):
    if not _staff_required(request):
        return JsonResponse({"message": "Staff access required."}, status=403)
    reviews = Review.objects.filter(status__in=("pending", "rejected")).select_related("dealership", "author").prefetch_related("photos").order_by("created_at")
    reports = ReviewReport.objects.filter(status="open").select_related("review", "review__dealership", "reporter").order_by("created_at")
    return JsonResponse({
        "reviews": [{
            "id": r.id, "dealer": r.dealership.full_name, "dealer_id": r.dealership_id,
            "author": r.name, "text": r.review, "rating": r.rating,
            "purchase": r.purchase, "verified_purchase": r.verified_purchase,
            "created_at": r.created_at.isoformat(),
            "photos": [p.image.url for p in r.photos.all()],
        } for r in reviews],
        "reports": [{
            "id": r.id, "review_id": r.review_id, "dealer": r.review.dealership.full_name,
            "review": r.review.review, "reporter": r.reporter.username,
            "reason": r.reason, "created_at": r.created_at.isoformat(),
        } for r in reports],
    })


@csrf_exempt
def moderate_review(request, review_id):
    if request.method != "POST":
        return JsonResponse({"message": "POST required."}, status=405)
    if not _staff_required(request):
        return JsonResponse({"message": "Staff access required."}, status=403)
    review = Review.objects.filter(id=review_id).first()
    if review is None:
        return JsonResponse({"message": "Review not found."}, status=404)
    data = _json_body(request) or {}
    action = data.get("action")
    if action == "approve":
        review.status = "approved"
    elif action == "reject":
        review.status = "rejected"
    elif action == "verify_purchase":
        if not review.purchase:
            return JsonResponse({"message": "Only purchase reviews can be verified."}, status=400)
        review.verified_purchase = True
    else:
        return JsonResponse({"message": "Choose approve, reject, or verify_purchase."}, status=400)
    review.save(update_fields=["status", "verified_purchase"])
    return JsonResponse({"review_status": review.status, "verified_purchase": review.verified_purchase})


@csrf_exempt
def moderate_report(request, report_id):
    if request.method != "POST":
        return JsonResponse({"message": "POST required."}, status=405)
    if not _staff_required(request):
        return JsonResponse({"message": "Staff access required."}, status=403)
    report = ReviewReport.objects.filter(id=report_id, status="open").first()
    if report is None:
        return JsonResponse({"message": "Open report not found."}, status=404)
    data = _json_body(request) or {}
    if data.get("action") not in ("resolve", "dismiss"):
        return JsonResponse({"message": "Choose resolve or dismiss."}, status=400)
    with transaction.atomic():
        report.status = "resolved" if data["action"] == "resolve" else "dismissed"
        report.save(update_fields=["status"])
        if report.status == "resolved":
            report.review.status = "rejected"
            report.review.save(update_fields=["status"])
    return JsonResponse({"report_status": report.status})


@csrf_exempt
def dealer_response(request, review_id):
    if request.method != "POST":
        return JsonResponse({"message": "POST required."}, status=405)
    if not _staff_required(request):
        return JsonResponse({"message": "Staff access required."}, status=403)
    review = Review.objects.filter(id=review_id, status="approved").first()
    if review is None:
        return JsonResponse({"message": "Approved review not found."}, status=404)
    data = _json_body(request) or {}
    response = str(data.get("response", "")).strip()
    if not response or len(response) > 2000:
        return JsonResponse({"message": "Response must contain 1 to 2,000 characters."}, status=400)
    reply, _ = DealerResponse.objects.update_or_create(
        review=review, defaults={"author": request.user, "response": response})
    return JsonResponse({"response": reply.response, "author": request.user.username})
