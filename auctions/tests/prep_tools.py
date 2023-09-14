from django.contrib import auth
from auctions.models import Listing

User = auth.get_user_model()


def create_registered_user(username, **kwargs) -> User:
    user, created = User.objects.get_or_create(username=username)
    if created:
        user.set_password("password")
        user.save()
    return user


def create_listing(**kwargs) -> Listing:
    watched_by = kwargs.pop("watched_by", None)
    listing = Listing.objects.create(**kwargs)
    if watched_by:
        listing.watchers.add(*watched_by)
        listing.save()
    listing.full_clean()
    return listing
