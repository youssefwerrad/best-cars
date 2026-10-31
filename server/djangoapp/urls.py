from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from . import views

app_name = "djangoapp"
urlpatterns = [
    path("register", views.registration, name="register"),
    path("login", views.login_user, name="login"),
    path("logout", views.logout_user, name="logout"),
    path("get_cars", views.get_cars, name="get_cars"),
    path("get_dealers", views.get_dealerships, name="get_dealers"),
    path("get_dealers/<str:state>", views.get_dealerships, name="get_dealers_by_state"),
    path("dealer/<int:dealer_id>", views.get_dealer_details, name="dealer_details"),
    path("reviews/dealer/<int:dealer_id>", views.get_dealer_reviews, name="dealer_reviews"),
    path("whoami", views.whoami, name="whoami"),
    path("cars/dealer/<int:dealer_id>", views.get_dealer_cars, name="dealer_cars"),
    path("add_review", views.add_review, name="add_review"),
    path("saved_dealers", views.saved_dealers, name="saved_dealers"),
    path("dealer/<int:dealer_id>/favorite", views.toggle_favorite, name="toggle_favorite"),
    path("reviews/<int:review_id>/helpful", views.helpful_vote, name="helpful_vote"),
    path("reviews/<int:review_id>/report", views.report_review, name="report_review"),
    path("reviews/<int:review_id>/response", views.dealer_response, name="dealer_response"),
    path("moderation", views.moderation_queue, name="moderation_queue"),
    path("moderation/reviews/<int:review_id>", views.moderate_review, name="moderate_review"),
    path("moderation/reports/<int:report_id>", views.moderate_report, name="moderate_report"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
