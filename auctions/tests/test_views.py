import contextlib
from decimal import Decimal
from pathlib import Path
from django.test import TestCase
from django.urls import reverse
from auctions.models import (
    BID_TOO_LOW_ERROR_MESSAGE,
    Listing,
    Bid,
    LISTING_CLOSED_ERROR,
)
from auctions.tests import prep_tools
from functional_tests.base import FunctionalTest
from auctions.tests.prep_tools import create_registered_user


@contextlib.contextmanager
def page_error_writer(lines: list, filename: str = None):
    try:
        yield
    except AssertionError as e:
        if filename:
            f = Path(__file__).parent / "screendumps" / filename
            f.write_bytes(lines)
            print(f"HTML Dumped to {str(f)}")
        else:
            print(lines)
        raise e


class CreateListingTest(TestCase):
    def setUp(self) -> None:
        self.user = prep_tools.create_registered_user("dave")
        self.client.force_login(self.user)
        return super().setUp()

    def test_uses_create_template(self):
        response = self.client.get(reverse("create-listing"))
        self.assertTemplateUsed(response, "auctions/listing_create_form.html")

    def test_redirects_if_listing_created(self):
        response = self.client.post(
            reverse("create-listing"),
            data={
                "title": "New Thing",
            },
        )
        self.assertRedirects(response, reverse("index"))

    def test_can_create_listing_with_just_title(self):
        self.client.post(
            reverse("create-listing"),
            data={
                "title": "New Thing",
            },
        )
        self.assertEqual(Listing.objects.count(), 1)
        listing = Listing.objects.first()
        self.assertEqual(listing.title, "New Thing")

    def test_can_create_listing_with_description(self):
        self.client.post(
            reverse("create-listing"),
            data={"title": "New Thing", "description": "Something Cool"},
        )
        listing = Listing.objects.first()
        self.assertEqual(listing.description, "Something Cool")

    def test_can_create_listing_with_category(self):
        self.client.post(
            reverse("create-listing"),
            data={"title": "New Thing", "category": Listing.FASHION},
        )
        listing = Listing.objects.first()
        self.assertEqual(listing.category, Listing.FASHION)

    def test_can_create_listing_with_starting_bid_and_currency(self):
        response = self.client.post(
            reverse("create-listing"),
            data={"title": "New Thing", "starting_bid": "2", "currency": "USD"},
        )
        self.assertRedirects(response, reverse("index"))
        listing = Listing.objects.first()
        self.assertEqual(listing.starting_bid.amount, 2.00)

    def test_invalid_starting_amount(self):
        response = self.client.post(
            reverse("create-listing"),
            data={"title": "New Thing", "starting_bid": "2x", "currency": "USD"},
        )
        self.assertContains(response, "Invalid starting bid")


class ActiveListingsTest(TestCase):
    def setUp(self) -> None:
        self.user = create_registered_user("joe")
        return super().setUp()

    def test_uses_index_template(self):
        response = self.client.get(reverse("index"))
        self.assertTemplateUsed(response, "auctions/index.html")

    def test_includes_title(self):
        Listing.objects.create(listed_by=self.user, title="Sweet Thing")
        response = self.client.get(reverse("index"))
        self.assertContains(response, "Sweet Thing")

    def test_includes_url_for_watchlist(self):
        response = self.client.get(reverse("index"))
        self.assertContains(response, reverse("watchlist"))

    def test_authenticated_user_sees_watchlist_count(self):
        self.user = prep_tools.create_registered_user("dave")
        listing = Listing.objects.create(listed_by=self.user, title="Sweet Thing")
        listing.watchers.add(self.user)
        listing.save()
        self.client.force_login(self.user)
        response = self.client.get(reverse("index"))
        with page_error_writer(response.content, "unit_test.html"):
            self.assertContains(
                response,
                '<span class="watchlist-count badge badge-secondary">1</span>',
                html=True,
            )

    def test_anonymous_user_cant_see_watchlist(self):
        self.user = prep_tools.create_registered_user("dave")
        listing = Listing.objects.create(listed_by=self.user, title="Sweet Thing")
        listing.watchers.add(self.user)
        listing.save()
        response = self.client.get(reverse("index"))
        self.assertNotContains(
            response,
            '<span class="watchlist-count badge badge-secondary">1</span>',
            html=True,
        )

    def test_only_shows_active_listings(self):
        message = "No listings so far"
        listing = Listing.objects.create(listed_by=self.user, title="Sweet Thing")
        listing.close(self.user)
        response = self.client.get(reverse("index"))
        self.assertEqual(response.context["empty_message"], message)
        with page_error_writer(response.content, "unit_test.html"):
            self.assertNotContains(response, "Sweet Thing")
            self.assertContains(response, message)

    def test_does_not_include_none_url_for_no_image_on_index(self):
        Listing.objects.create(listed_by=self.user, title="Sweet Thing")
        response = self.client.get(reverse("index"))
        with page_error_writer(response.content, "unit_test.html"):
            self.assertNotContains(response, 'src="None"')


class ExistingListingTest(TestCase):
    def setUp(self) -> None:
        self.user = create_registered_user("joe")
        self.client.force_login(self.user)
        return super().setUp()

    def test_uses_template(self):
        listing = Listing.objects.create(title="Sweet Thing", listed_by=self.user)
        response = self.client.get(reverse("listing-detail", args=[listing.pk]))
        self.assertTemplateUsed(response, "auctions/listing_detail.html")

    def test_includes_details(self):
        details = {
            "title": "Sweet Thing",
            "image_url": FunctionalTest.IMAGE_URL,
            "description": "a must have",
            "starting_bid": "5.00",
            "category": Listing.TOYS,
        }
        listing = Listing.objects.create(listed_by=self.user, **details)
        response = self.client.get(reverse("listing-detail", args=[listing.pk]))
        with page_error_writer(response.content, "unit_test.html"):
            for detail in details.values():
                self.assertContains(response, detail)

    def test_does_not_include_none_url_for_no_image_on_detail(self):
        listing = Listing.objects.create(listed_by=self.user, title="Sweet Thing")
        response = self.client.get(reverse("listing-detail", args=[listing.pk]))
        with page_error_writer(response.content, "unit_test.html"):
            self.assertNotContains(response, 'src="None"')

    def test_add_watcher(self):
        listing = Listing.objects.create(title="Sweet Thing", listed_by=self.user)
        response = self.client.post(
            reverse("listing-detail", args=[listing.pk]),
            data={"action": "add-remove-from-watchlist"},
        )
        self.assertRedirects(response, listing.get_absolute_url())
        listing.refresh_from_db()
        self.assertEqual(listing.title, "Sweet Thing", "title error")
        self.assertIn(self.user, listing.watchers.all())

    def test_anonymous_user_cannot_add_to_watchlist(self):
        listing = Listing.objects.create(title="Sweet Thing", listed_by=self.user)
        self.client.logout()
        response = self.client.post(
            reverse("listing-detail", args=[listing.pk]),
            data={"action": "add-remove-from-watchlist"},
        )
        self.assertRedirects(response, reverse("login"))

    def test_anonymous_user_asking_for_watchlist_does_not_cause_error(self):
        Listing.objects.create(title="Sweet Thing", listed_by=self.user)
        self.client.logout()
        self.client.get(reverse("watchlist"))

    def test_remove_watcher(self):
        listing = Listing.objects.create(title="Sweet Thing", listed_by=self.user)
        listing.watchers.add(self.user)
        response = self.client.post(
            reverse("listing-detail", args=[listing.pk]),
            data={"action": "add-remove-from-watchlist"},
        )
        self.assertRedirects(response, listing.get_absolute_url())
        listing.refresh_from_db()
        self.assertEqual(listing.title, "Sweet Thing", "title error")
        self.assertNotIn(self.user, listing.watchers.all())

    def test_user_knows_if_they_are_watching_the_item_they_are_viewing(self):
        listing = Listing.objects.create(title="Sweet Thing", listed_by=self.user)
        listing.watchers.add(self.user)
        response = self.client.get(reverse("listing-detail", args=[listing.pk]))
        with page_error_writer(response.content, "unit_test.html"):
            self.assertContains(response, "badge-info")

    def test_includes_number_of_bids(self):
        listing = Listing.objects.create(title="Sweet Thing", listed_by=self.user)
        Bid.objects.create(listing=listing, amount=5.00, bidder=self.user)
        response = self.client.get(reverse("listing-detail", args=[listing.pk]))
        with page_error_writer(response.content, "unit_test.html"):
            self.assertContains(response, '<span class="bid-count">1</span>', html=True)

    def test_user_knows_if_they_are_highest_bidder(self):
        user_max = create_registered_user("max")
        listing = Listing.objects.create(title="thing", listed_by=self.user)
        Bid.objects.create(listing=listing, amount=4.00, bidder=user_max)
        response = self.client.get(reverse("listing-detail", args=[listing.pk]))
        with page_error_writer(response.content, "unit_test.html"):
            self.assertContains(
                response, '<span class="is-current-bid">is not</span>', html=True
            )
        Bid.objects.create(listing=listing, amount=5.00, bidder=self.user)
        response = self.client.get(reverse("listing-detail", args=[listing.pk]))
        with page_error_writer(response.content, "unit_test.html"):
            self.assertContains(
                response, '<span class="is-current-bid">is</span>', html=True
            )

    def test_user_can_bid_on_listing(self):
        listing = Listing.objects.create(title="Sweet Thing", listed_by=self.user)
        response = self.client.post(
            reverse("listing-detail", args=[listing.pk]),
            data={"action": "place-a-bid", "amount": "5.00"},
        )
        self.assertRedirects(response, listing.get_absolute_url())
        bid = listing.bids.first()
        self.assertEqual(bid.bidder, self.user)
        self.assertEqual(bid.amount.amount, Decimal("5.00"))

    def test_user_cannot_bid_on_closed_listing(self):
        listing = Listing.objects.create(title="Sweet Thing", listed_by=self.user)
        listing.close(self.user)
        response = self.client.post(
            reverse("listing-detail", args=[listing.pk]),
            data={"action": "place-a-bid", "amount": "5.00"},
        )
        self.assertIn(
            LISTING_CLOSED_ERROR,
            [error for error in response.context["form"].errors["__all__"]],
        )
        with page_error_writer(response.content, "unit_test.html"):
            self.assertContains(response, LISTING_CLOSED_ERROR)
        self.assertIsNone(listing.bids.first())

    def test_anonymous_users_cannot_place_bids(self):
        listing = Listing.objects.create(title="Sweet Thing", listed_by=self.user)
        self.client.logout()
        self.client.post(
            reverse("listing-detail", args=[listing.pk]),
            data={"action": "place-a-bid", "amount": "5.00"},
        )
        self.assertIsNone(listing.bids.first())

    def test_bid_must_be_at_least_equal_to_starting_bid(self):
        listing = Listing.objects.create(
            title="Sweet Thing", listed_by=self.user, starting_bid=5.00
        )
        response = self.client.post(
            reverse("listing-detail", args=[listing.pk]),
            data={"action": "place-a-bid", "amount": "4.00"},
        )
        self.assertTemplateUsed(response, "auctions/listing_detail.html")
        self.assertIn(
            BID_TOO_LOW_ERROR_MESSAGE,
            [error for error in response.context["form"].errors["amount"]],
        )
        with page_error_writer(response.content, "unit_test.html"):
            self.assertContains(response, BID_TOO_LOW_ERROR_MESSAGE)
        self.assertIsNone(listing.bids.first())

        response = self.client.post(
            reverse("listing-detail", args=[listing.pk]),
            data={"action": "place-a-bid", "amount": "5.00"},
        )
        self.assertRedirects(response, listing.get_absolute_url())
        self.assertEqual(listing.bids.first().bidder, self.user)

    def test_bid_must_be_greater_than_other_bids(self):
        bob = create_registered_user(username="bob")
        listing = Listing.objects.create(
            title="Sweet Thing", listed_by=self.user, starting_bid=5.00
        )
        Bid.objects.create(listing=listing, amount=6.00, bidder=bob)
        response = self.client.post(
            reverse("listing-detail", args=[listing.pk]),
            data={"action": "place-a-bid", "amount": "5.50"},
        )
        self.assertTemplateUsed(response, "auctions/listing_detail.html")
        self.assertContains(response, BID_TOO_LOW_ERROR_MESSAGE)
        self.assertEqual(listing.bids.first().bidder, bob)

    def test_listed_by_user_can_close_listing(self):
        bob = create_registered_user(username="bob")
        listing = Listing.objects.create(
            title="Sweet Thing", listed_by=self.user, starting_bid=5.00
        )
        Bid.objects.create(listing=listing, amount=6.00, bidder=bob)
        response = self.client.post(
            reverse("listing-detail", args=[listing.pk]),
            data={"action": "close-listing"},
        )
        self.assertRedirects(response, listing.get_absolute_url())
        listing.refresh_from_db()
        self.assertTrue(listing.closed)
        self.assertEqual(listing.winner, bob)

    def test_add_a_comment_to_listing(self):
        listing = Listing.objects.create(
            title="Sweet Thing", listed_by=self.user, starting_bid=5.00
        )
        response = self.client.post(
            reverse("listing-detail", args=[listing.pk]),
            data={"action": "add-comment", "comment": "best thing ever"},
        )
        self.assertRedirects(response, listing.get_absolute_url())
        listing.refresh_from_db()
        self.assertEqual(listing.comments.first().text, "best thing ever")

    def test_comments_are_shown_on_the_page(self):
        listing = Listing.objects.create(
            title="Sweet Thing", listed_by=self.user, starting_bid=5.00
        )
        listing.comments.create(commenter=self.user, text="piece o trash")
        listing.comments.create(commenter=self.user, text="work of art")

        response = self.client.get(reverse("listing-detail", args=[listing.pk]))
        with page_error_writer(response.content, "unit_test.html"):
            self.assertContains(response, "piece o trash")
            self.assertContains(response, "work of art")


class WatchlistTest(TestCase):
    def setUp(self) -> None:
        self.user = create_registered_user("joe")
        self.client.force_login(self.user)
        return super().setUp()

    def test_uses_right_template(self):
        response = self.client.get(reverse("watchlist"))
        self.assertTemplateUsed(response, "auctions/index.html")

    def test_doesnt_include_unwatched_listings(self):
        Listing.objects.create(
            title="Buy This", listed_by=self.user, starting_bid=5.00
        ).watchers.add(self.user)
        Listing.objects.create(
            title="Sweet Thing", listed_by=self.user, starting_bid=5.00
        )
        response = self.client.get(reverse("watchlist"))
        with page_error_writer(response.content, "unit_test.html"):
            self.assertContains(response, "Buy This")
            self.assertNotContains(response, "Sweet Thing")

    def test_no_watching_listings_empty_message(self):
        message = "You are not watching any listings yet"
        response = self.client.get(reverse("watchlist"))
        self.assertEqual(response.context["empty_message"], message)
        with page_error_writer(response.content, "unit_test.html"):
            self.assertContains(response, message)


class CategoryTest(TestCase):
    def setUp(self) -> None:
        self.user = create_registered_user("joe")
        self.client.force_login(self.user)
        return super().setUp()

    def test_uses_right_template(self):
        response = self.client.get(reverse("categories"))
        self.assertTemplateUsed(response, "auctions/categories.html")

    def test_categories_in_context_data(self):
        response = self.client.get(reverse("categories"))
        with page_error_writer(response.content, "unit_test.html"):
            for category in Listing.CATEGORY_CHOICES:
                self.assertIn(category, response.context["categories"])

    def test_lists_categories(self):
        # checking for query name
        response = self.client.get(reverse("categories"))
        with page_error_writer(response.content, "unit_test.html"):
            for _, category in Listing.CATEGORY_CHOICES:
                self.assertContains(response, f">{category}<")

    def test_lists_category_link(self):
        # checking for select name
        response = self.client.get(reverse("categories"))
        with page_error_writer(response.content, "unit_test.html"):
            for category, _ in Listing.CATEGORY_CHOICES:
                self.assertContains(
                    response, reverse("listings-in-category", args=[category])
                )

    def test_listings_in_category_uses_right_template(self):
        response = self.client.get(reverse("listings-in-category", args=[Listing.TOYS]))
        self.assertTemplateUsed(response, "auctions/index.html")

    def test_listings_in_category_passes_correct_context(self):
        response = self.client.get(reverse("listings-in-category", args=[Listing.TOYS]))
        self.assertEqual(
            response.context["body_title"],
            "Listings in Selected Category",
        )
        self.assertEqual(
            response.context["empty_message"],
            "There are no Listings in this Category",
        )

    def test_listings_in_category_context(self):
        l1 = Listing.objects.create(
            title="Gadget", category=Listing.TOYS, listed_by=self.user
        )
        l2 = Listing.objects.create(
            title="Other", category=Listing.FASHION, listed_by=self.user
        )
        l3 = Listing.objects.create(title="Nope", listed_by=self.user)
        response = self.client.get(reverse("listings-in-category", args=[Listing.TOYS]))
        self.assertIn(l1, response.context["object_list"])
        self.assertNotIn(l2, response.context["object_list"])
        self.assertNotIn(l3, response.context["object_list"])

    def test_listings_in_category_template(self):
        l1 = Listing.objects.create(
            title="Gadget", category=Listing.TOYS, listed_by=self.user
        )
        l2 = Listing.objects.create(
            title="Other", category=Listing.FASHION, listed_by=self.user
        )
        l3 = Listing.objects.create(title="Nope", listed_by=self.user)
        response = self.client.get(reverse("listings-in-category", args=[Listing.TOYS]))
        with page_error_writer(response.content, "unit_test.html"):
            self.assertContains(response, l1.title)
            self.assertNotContains(response, l2.title)
            self.assertNotContains(response, l3.title)
