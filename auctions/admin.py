from django.contrib import admin
from auctions.models import Listing, Comment, Bid, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username",)


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    filter_horizontal = ("watchers",)
    list_display = (
        "title",
        "description",
        "starting_bid",
        "category",
        "listed_by",
        "closed",
    )


@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = ("listing", "amount", "bidder")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("listing", "commenter", "text")
