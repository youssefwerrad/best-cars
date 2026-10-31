from io import BytesIO
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from django.test import TestCase
from PIL import Image

from .models import Car, Dealer, DealerFavorite, HelpfulVote, Review, ReviewPhoto, ReviewReport
from .restapis import analyze_review_sentiments


class ApiTests(TestCase):
    def setUp(self):
        media = tempfile.TemporaryDirectory()
        media_override = override_settings(MEDIA_ROOT=media.name)
        media_override.enable()
        self.addCleanup(media_override.disable)
        self.addCleanup(media.cleanup)
        self.d = Dealer.objects.create(city="X", state="Texas", st="TX", address="a", zip="1",
                                       lat=0, long=0, short_name="s", full_name="S Motors")
        User.objects.create_user("u", password="pw12345678")

    def post(self, path, data):
        return self.client.post(f"/djangoapp/{path}", json.dumps(data), content_type="application/json")

    def test_dealers_and_filter(self):
        self.assertEqual(len(self.client.get("/djangoapp/get_dealers").json()["dealers"]), 1)
        self.assertEqual(self.client.get("/djangoapp/get_dealers/Ohio").json()["dealers"], [])

    def test_uploaded_media_is_separate_from_collected_static(self):
        media_root = Path(settings.MEDIA_ROOT).resolve()
        static_root = Path(settings.STATIC_ROOT).resolve()
        self.assertNotEqual(media_root, static_root)
        self.assertNotIn(static_root, media_root.parents)

    def test_review_requires_login(self):
        r = self.post("add_review", {"dealership": self.d.id, "review": "hi"})
        self.assertEqual(r.status_code, 403)

    def test_csrf_protects_login_and_authenticated_mutations(self):
        client = Client(enforce_csrf_checks=True)
        login_payload = json.dumps({"userName": "u", "password": "pw12345678"})
        self.assertEqual(client.post(
            "/djangoapp/login", login_payload, content_type="application/json").status_code, 403)

        client.get("/djangoapp/whoami")
        csrf_token = client.cookies["csrftoken"].value
        self.assertEqual(client.post(
            "/djangoapp/login", login_payload, content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token).status_code, 200)
        csrf_token = client.cookies["csrftoken"].value

        favorite_path = f"/djangoapp/dealer/{self.d.id}/favorite"
        favorite_payload = json.dumps({"favorite": True})
        self.assertEqual(client.post(
            favorite_path, favorite_payload, content_type="application/json").status_code, 403)
        self.assertFalse(DealerFavorite.objects.exists())
        self.assertEqual(client.post(
            favorite_path, favorite_payload, content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token).status_code, 200)

        review = Review.objects.create(
            dealership=self.d, name="u", review="Needs moderation.",
            author=User.objects.get(username="u"), rating=4, status="pending")
        moderator = User.objects.create_user("moderator", "pw12345678", is_staff=True)
        staff_client = Client(enforce_csrf_checks=True)
        staff_client.force_login(moderator)
        staff_client.get("/djangoapp/whoami")
        staff_csrf_token = staff_client.cookies["csrftoken"].value
        moderation_path = f"/djangoapp/moderation/reviews/{review.id}"
        moderation_payload = json.dumps({"action": "approve"})
        self.assertEqual(staff_client.post(
            moderation_path, moderation_payload, content_type="application/json").status_code, 403)
        self.assertEqual(review.status, "pending")
        self.assertEqual(staff_client.post(
            moderation_path, moderation_payload, content_type="application/json",
            HTTP_X_CSRFTOKEN=staff_csrf_token).status_code, 200)
        review.refresh_from_db()
        self.assertEqual(review.status, "approved")

    def test_logout_requires_csrf_protected_post(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(User.objects.get(username="u"))
        self.assertEqual(client.get("/djangoapp/logout").status_code, 405)
        client.get("/djangoapp/whoami")
        self.assertEqual(client.post(
            "/djangoapp/logout",
            HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value).status_code, 200)

    def test_login_review_whoami(self):
        self.assertEqual(self.post("login", {"userName": "u", "password": "pw12345678"}).json()["status"], "Authenticated")
        self.assertEqual(self.client.get("/djangoapp/whoami").json()["userName"], "u")
        self.assertEqual(self.post("add_review", {
            "dealership": self.d.id, "review": "great", "rating": 5, "recommend": True,
        }).json()["status"], 200)
        self.assertEqual(self.post("add_review", {"dealership": self.d.id, "review": " "}).json()["status"], 400)

    def test_sentiment_is_computed_when_review_is_written_and_reused(self):
        self.client.login(username="u", password="pw12345678")
        review_text = "Great service / quick answers? Absolutely #1!"
        with patch("djangoapp.views.analyze_review_sentiments", return_value="positive") as analyze:
            response = self.post("add_review", {
                "dealership": self.d.id, "review": review_text, "rating": 5, "recommend": True,
            })
        self.assertEqual(response.status_code, 200, response.json())
        analyze.assert_called_once_with(review_text)

        review = Review.objects.get(pk=response.json()["review_id"])
        self.assertEqual(review.sentiment, "positive")
        review.status = "approved"
        review.save(update_fields=["status"])
        with patch("djangoapp.views.analyze_review_sentiments", side_effect=AssertionError("must not run on list")):
            listed = self.client.get(f"/djangoapp/reviews/dealer/{self.d.id}")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["reviews"][0]["sentiment"], "positive")

    def test_sentiment_service_receives_text_as_json_not_url_path(self):
        with patch("djangoapp.restapis.requests.post") as post:
            post.return_value.json.return_value = {"sentiment": "negative"}
            self.assertEqual(
                analyze_review_sentiments("bad /service? #review"),
                "negative",
            )
        post.assert_called_once()
        self.assertTrue(post.call_args.args[0].endswith("/analyze"))
        self.assertEqual(post.call_args.kwargs["json"], {"text": "bad /service? #review"})

    def test_register_duplicate(self):
        self.assertIn("error", self.post("register", {"userName": "u", "password": "x"}).json())

    def test_review_moderation_rating_and_dealer_response(self):
        self.client.login(username="u", password="pw12345678")
        response = self.post("add_review", {
            "dealership": self.d.id, "review": "Helpful service.", "rating": 4,
            "recommend": False, "purchase": True,
        })
        self.assertEqual(response.status_code, 200, response.json())
        review_id = response.json()["review_id"]
        review = Review.objects.get(pk=review_id)
        self.assertEqual(review.status, "pending")
        self.assertFalse(review.verified_purchase)
        self.assertEqual(self.client.get(f"/djangoapp/reviews/dealer/{self.d.id}").json()["reviews"], [])

        moderator = User.objects.create_user("moderator", password="pw12345678", is_staff=True)
        staff_client = self.client_class()
        staff_client.force_login(moderator)
        verify = staff_client.post(
            f"/djangoapp/moderation/reviews/{review_id}",
            json.dumps({"action": "verify_purchase"}), content_type="application/json")
        self.assertEqual(verify.status_code, 200)
        self.assertTrue(verify.json()["verified_purchase"])
        approve = staff_client.post(
            f"/djangoapp/moderation/reviews/{review_id}",
            json.dumps({"action": "approve"}), content_type="application/json")
        self.assertEqual(approve.status_code, 200)
        dealer_summary = self.client.get(f"/djangoapp/dealer/{self.d.id}").json()["dealer"][0]
        self.assertEqual(dealer_summary["average_rating"], 4.0)
        self.assertEqual(dealer_summary["review_count"], 1)
        response = staff_client.post(
            f"/djangoapp/reviews/{review_id}/response",
            json.dumps({"response": "Thank you for visiting."}), content_type="application/json")
        self.assertEqual(response.status_code, 200, response.json())

        public = self.client.get(f"/djangoapp/reviews/dealer/{self.d.id}").json()["reviews"]
        self.assertEqual(public[0]["rating"], 4)
        self.assertTrue(public[0]["verified_purchase"])
        self.assertEqual(public[0]["response"]["text"], "Thank you for visiting.")
        self.assertFalse(public[0]["recommend"])

    def test_helpful_votes_and_review_reports_require_authentication(self):
        review = Review.objects.create(
            dealership=self.d, name="u", review="Good experience.",
            author=User.objects.get(username="u"), rating=5, status="approved")
        self.assertEqual(self.client.post(f"/djangoapp/reviews/{review.id}/helpful").status_code, 403)
        self.client.login(username="u", password="pw12345678")
        first = self.client.post(f"/djangoapp/reviews/{review.id}/helpful")
        second = self.client.post(f"/djangoapp/reviews/{review.id}/helpful")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(HelpfulVote.objects.filter(review=review).count(), 1)
        reported = self.post(f"reviews/{review.id}/report", {"reason": "Spam or advertising"})
        duplicate = self.post(f"reviews/{review.id}/report", {"reason": "Spam or advertising"})
        self.assertEqual(reported.status_code, 201)
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(ReviewReport.objects.filter(review=review).count(), 1)

    def test_saved_dealers_and_paginated_inventory_filters(self):
        Car.objects.create(dealer=self.d, make="Honda", model="Civic", body_type="Sedan", year=2022, mileage=12000)
        matching = self.client.get("/djangoapp/get_dealers?make=Honda&body_type=Sedan&page_size=1").json()
        self.assertEqual(len(matching["dealers"]), 1)
        self.assertEqual(matching["dealers"][0]["inventory_count"], 1)
        self.assertEqual(matching["dealers"][0]["average_rating"], None)
        self.assertEqual(self.client.get("/djangoapp/saved_dealers").status_code, 403)
        self.client.login(username="u", password="pw12345678")
        saved = self.post(f"dealer/{self.d.id}/favorite", {"favorite": True})
        self.assertTrue(saved.json()["is_favorite"])
        self.assertEqual(self.client.get("/djangoapp/saved_dealers").json()["dealers"][0]["id"], self.d.id)
        removed = self.post(f"dealer/{self.d.id}/favorite", {"favorite": False})
        self.assertFalse(removed.json()["is_favorite"])
        self.assertEqual(DealerFavorite.objects.count(), 0)

    def test_review_upload_rating_validation_and_admin_report_actions(self):
        self.client.login(username="u", password="pw12345678")
        self.assertEqual(self.post("add_review", {
            "dealership": self.d.id, "review": "Missing stars", "recommend": True,
        }).status_code, 400)
        image_buffer = BytesIO()
        Image.new("RGB", (4, 4), color="teal").save(image_buffer, format="PNG")
        image = SimpleUploadedFile("lot.png", image_buffer.getvalue(), content_type="image/png")
        response = self.client.post("/djangoapp/add_review", {
            "dealership": str(self.d.id), "review": "A photo review.",
            "rating": "5", "recommend": "true", "purchase": "false",
            "photos": [image],
        })
        self.assertEqual(response.status_code, 200, response.json())
        self.assertEqual(ReviewPhoto.objects.filter(review_id=response.json()["review_id"]).count(), 1)
        gif_buffer = BytesIO()
        Image.new("RGB", (4, 4), color="teal").save(gif_buffer, format="GIF")
        unsupported = SimpleUploadedFile("lot.gif", gif_buffer.getvalue(), content_type="image/gif")
        invalid_photo = self.client.post("/djangoapp/add_review", {
            "dealership": str(self.d.id), "review": "Unsupported photo.",
            "rating": "5", "recommend": "true", "purchase": "false",
            "photos": [unsupported],
        })
        self.assertEqual(invalid_photo.status_code, 400)

        moderator = User.objects.create_user("moderator", password="pw12345678", is_staff=True)
        staff_client = self.client_class()
        staff_client.force_login(moderator)
        review_id = response.json()["review_id"]
        staff_client.post(
            f"/djangoapp/moderation/reviews/{review_id}",
            json.dumps({"action": "approve"}), content_type="application/json")
        self.post(f"reviews/{review_id}/report", {"reason": "Other"})
        report_id = ReviewReport.objects.get(review_id=review_id).id
        resolved = staff_client.post(
            f"/djangoapp/moderation/reports/{report_id}",
            json.dumps({"action": "resolve"}), content_type="application/json")
        self.assertEqual(resolved.json()["report_status"], "resolved")
        self.assertEqual(Review.objects.get(pk=review_id).status, "rejected")
        self.assertEqual(staff_client.get("/djangoapp/moderation").status_code, 200)

    def test_moderation_and_dealer_response_are_staff_only(self):
        review = Review.objects.create(
            dealership=self.d, name="u", review="Good experience.",
            author=User.objects.get(username="u"), rating=5, status="approved")
        self.assertEqual(self.client.get("/djangoapp/moderation").status_code, 403)
        self.client.login(username="u", password="pw12345678")
        response = self.post(f"reviews/{review.id}/response", {"response": "Thanks"})
        self.assertEqual(response.status_code, 403)

    def test_dealer_directory_sort_and_pages(self):
        Dealer.objects.create(city="Y", state="Texas", st="TX", address="b", zip="2",
                              lat=1, long=1, short_name="t", full_name="T Motors")
        first = self.client.get("/djangoapp/get_dealers?page=1&page_size=1&sort=name")
        second = self.client.get("/djangoapp/get_dealers?page=2&page_size=1&sort=name")
        self.assertEqual(first.json()["pages"], 2)
        self.assertEqual(first.json()["dealers"][0]["full_name"], "S Motors")
        self.assertEqual(second.json()["dealers"][0]["full_name"], "T Motors")

    def test_dealer_reviews_are_paginated(self):
        for number in range(3):
            Review.objects.create(
                dealership=self.d, name=f"Driver {number}", review=f"Review {number}",
                rating=number + 1, status="approved")
        first = self.client.get(f"/djangoapp/reviews/dealer/{self.d.id}?page=1&page_size=2")
        second = self.client.get(f"/djangoapp/reviews/dealer/{self.d.id}?page=2&page_size=2")
        self.assertEqual((first.json()["total"], first.json()["pages"], first.json()["page"]), (3, 2, 1))
        self.assertEqual(len(first.json()["reviews"]), 2)
        self.assertEqual(second.json()["page"], 2)
        self.assertEqual(len(second.json()["reviews"]), 1)
