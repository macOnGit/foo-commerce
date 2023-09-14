from decimal import Decimal
from django.contrib.auth.models import AbstractUser
from djmoney.models.fields import MoneyField
from django.db import models
from django.urls import reverse
from django.conf import settings
from django.core.exceptions import ValidationError

BID_TOO_LOW_ERROR_MESSAGE = (
    "Bid must be at least as large as the starting bid, and must be greater "
    "than any other bids that have been placed."
)

LISTING_CLOSED_ERROR = "You cannot place a bid on a closed listing."


class User(AbstractUser):
    pass


class Listing(models.Model):
    FASHION = "Fashion"
    TOYS = "Toys"
    ELECTRONICS = "Electronics"
    HOME = "Home"
    CATEGORY_CHOICES = [
        (FASHION, "Fashion"),
        (TOYS, "Toys"),
        (ELECTRONICS, "Electronics"),
        (HOME, "Home"),
    ]
    title = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    # https://djangolearn.com/p/money-fields-for-django-forms-and-models
    starting_bid = MoneyField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        default=Decimal("0.00"),
        default_currency="USD",
    )
    image_url = models.URLField(null=True, blank=True)
    category = models.CharField(
        max_length=100, null=True, blank=True, choices=CATEGORY_CHOICES
    )
    watchers = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="watching"
    )
    listed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="listings"
    )
    created = models.DateTimeField(auto_now_add=True)
    closed = models.BooleanField(default=False)

    def __repr__(self) -> str:
        return (
            f'Listing(title="{self.title}", '
            f'description="{self.description}", '
            f'price="{self.price}", '
            f'category="{self.category}")'
        )

    def __str__(self) -> str:
        return self.title

    @property
    def highest_bidder(self):
        try:
            return self.bids.order_by("-amount").first().bidder
        except AttributeError:
            pass

    @property
    def highest_bid(self):
        try:
            return self.bids.order_by("-amount").first().amount
        except AttributeError:
            pass

    @property
    def price(self):
        return self.highest_bid if self.bids.count() else self.starting_bid

    def get_absolute_url(self):
        return reverse("listing-detail", kwargs={"pk": self.pk})

    def add_remove_from_watchlist(self, user):
        if user not in self.watchers.all():
            self.watchers.add(user)
        else:
            self.watchers.remove(user)

    def close(self, user):
        if self.listed_by == user:
            self.closed = True
            self.save()

    @property
    def winner(self):
        if self.closed:
            return self.highest_bidder


class Bid(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="bids")
    amount = MoneyField(
        max_digits=14, decimal_places=2, null=True, blank=True, default_currency="USD"
    )
    bidder = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bids"
    )

    def clean(self) -> None:
        if self.listing.closed:
            raise ValidationError({None: LISTING_CLOSED_ERROR})
        if (
            self.listing.starting_bid and (self.listing.starting_bid > self.amount)
        ) or (self.listing.bids.count() and (self.listing.highest_bid >= self.amount)):
            raise ValidationError({"amount": BID_TOO_LOW_ERROR_MESSAGE})
        return super().clean()

    def __repr__(self) -> str:
        return f"Bid('{self.listing}', '{self.amount}', {self.bidder})"


class Comment(models.Model):
    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="comments", default=None
    )
    commenter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comments",
        default=None,
    )
    text = models.TextField(blank=True)
