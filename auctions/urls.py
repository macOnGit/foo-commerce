from django.urls import path

from . import views

urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("register", views.register, name="register"),
    path("create-listing", views.ListingCreateView.as_view(), name="create-listing"),
    path("listings/<int:pk>", views.ListingUpdateView.as_view(), name="listing-detail"),
    path("closed-listings", views.ClosedListingView.as_view(), name="closed-listings"),
    path("watchlist", views.WatchlistView.as_view(), name="watchlist"),
    path("categories", views.CategoriesView.as_view(), name="categories"),
    path(
        "listings-in-category/<str:category>",
        views.ListingsInCategory.as_view(),
        name="listings-in-category",
    ),
]
