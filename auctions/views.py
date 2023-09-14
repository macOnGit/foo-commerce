from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponseRedirect
from typing import Any, Dict
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.views.generic.edit import CreateView, FormMixin
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic import TemplateView
from djmoney.money import Money
from .models import User, Listing, Bid
from .forms import CreateListingForm, ListingForm
from django.core.exceptions import ValidationError


class IndexView(ListView):
    template_name = "auctions/index.html"
    extra_context = {
        "body_title": "Active Listings",
        "empty_message": "No listings so far",
    }
    queryset = Listing.objects.filter(closed=False)


class ListingCreateView(LoginRequiredMixin, CreateView):
    model = Listing
    form_class = CreateListingForm
    template_name = "auctions/listing_create_form.html"
    success_url = reverse_lazy("index")
    login_url = reverse_lazy("login")

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.
        starting_bid = form.data.get("starting_bid_0")
        currency = form.data.get("starting_bid_1")
        if starting_bid and currency:
            form.instance.starting_bid = Money(starting_bid, currency)
        form.instance.listed_by = self.request.user
        return super().form_valid(form)


class ListingUpdateView(DetailView, FormMixin):
    model = Listing
    form_class = ListingForm

    def post(self, request, *args, **kwargs):
        listing = self.get_object()
        if self.request.user.is_anonymous:
            return HttpResponseRedirect(reverse("login"))
        if request.POST["action"] == "add-remove-from-watchlist":
            listing.add_remove_from_watchlist(self.request.user)
        elif request.POST["action"] == "place-a-bid":
            amount = request.POST["amount"]
            try:
                bid = Bid(listing=listing, amount=amount, bidder=self.request.user)
                bid.full_clean()
                bid.save()
            except ValidationError as e:
                self.object = listing
                form = self.get_form()
                for key, value_list in e.error_dict.items():
                    for value in value_list:
                        form.add_error(key, value)
                context = self.get_context_data(form=form)
                return self.render_to_response(context=context)
        elif request.POST["action"] == "close-listing":
            listing.close(self.request.user)
        elif request.POST["action"] == "add-comment":
            listing.comments.create(
                commenter=self.request.user, text=request.POST["comment"]
            )
        return HttpResponseRedirect(listing.get_absolute_url())

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["is_watched_by_user"] = self.request.user in self.object.watchers.all()
        context["user_is_highest_bidder"] = (
            self.object.highest_bidder == self.request.user
        )
        return context


class WatchlistView(LoginRequiredMixin, IndexView):
    login_url = reverse_lazy("login")
    extra_context = {
        "body_title": "Your Watchlist",
        "empty_message": "You are not watching any listings yet",
    }

    def get_queryset(self):
        try:
            return self.request.user.watching.all()
        except AttributeError:
            return Listing.objects.none()


class ListingsInCategory(IndexView):

    extra_context = {
        "body_title": "Listings in Selected Category",
        "empty_message": "There are no Listings in this Category",
    }

    def get_queryset(self):
        return Listing.objects.filter(category=self.kwargs["category"])


class ClosedListingView(IndexView):
    queryset = Listing.objects.filter(closed=True)
    extra_context = {
        "body_title": "Closed Listings",
        "empty_message": "There are no closed listings yet",
    }


class CategoriesView(TemplateView):
    template_name = "auctions/categories.html"
    extra_context = {
        "body_title": "Categorized Listings",
    }

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["categories"] = Listing.CATEGORY_CHOICES
        return context


def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(
                request,
                "auctions/login.html",
                {"message": "Invalid username and/or password."},
            )
    else:
        return render(request, "auctions/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(
                request, "auctions/register.html", {"message": "Passwords must match."}
            )

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(
                request,
                "auctions/register.html",
                {"message": "Username already taken."},
            )
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "auctions/register.html")
