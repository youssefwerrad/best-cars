from django.contrib import admin
from .models import (
    CarMake, CarModel, Car, Dealer, DealerFavorite, DealerResponse,
    HelpfulVote, Review, ReviewPhoto, ReviewReport,
)


class ReviewPhotoInline(admin.TabularInline):
    model = ReviewPhoto
    extra = 0


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "dealership", "name", "rating", "status", "verified_purchase", "created_at")
    list_filter = ("status", "verified_purchase", "purchase", "recommend")
    search_fields = ("name", "review", "dealership__full_name")
    readonly_fields = ("created_at",)
    inlines = [ReviewPhotoInline]


@admin.register(ReviewReport)
class ReviewReportAdmin(admin.ModelAdmin):
    list_display = ("id", "review", "reporter", "status", "created_at")
    list_filter = ("status",)
    readonly_fields = ("created_at",)


admin.site.register([
    CarMake, CarModel, Car, Dealer, DealerFavorite, DealerResponse, HelpfulVote,
])
