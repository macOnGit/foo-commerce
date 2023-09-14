from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from auctions.models import Listing, Bid
from auctions.tests.prep_tools import create_registered_user


class ListingTest(TestCase):
    def setUp(self) -> None:
        self.user = create_registered_user("joe")
        return super().setUp()

    def test_listing_only_needs_title_and_listed_by(self):
        Listing.objects.create(title="thing", listed_by=self.user)

    def test_listing_can_have_description(self):
        Listing.objects.create(
            title="thing", description="cool gadget", listed_by=self.user
        )

    def test_listing_can_have_starting_bid(self):
        listing = Listing.objects.create(
            listed_by=self.user, title="thing", starting_bid=2
        )
        self.assertEqual(listing.starting_bid.amount, 2.00)

    def test_invalid_staring_bid_raises_validationerror(self):
        with self.assertRaises(ValidationError):
            Listing.objects.create(title="thing", starting_bid="2x")

    def test_listing_can_have_category(self):
        Listing.objects.create(
            listed_by=self.user, title="thing", category=Listing.FASHION
        )

    def test_listing_can_have_image_url(self):
        Listing.objects.create(
            listed_by=self.user, title="thing", image_url="https://image.com"
        )

    def test_listing_can_have_watchers(self):
        user_joe = self.user
        user_max = create_registered_user("max")
        listing = Listing.objects.create(listed_by=self.user, title="thing")
        listing.watchers.add(user_joe, user_max)
        self.assertIn(user_joe, listing.watchers.all(), "joe not added")
        self.assertIn(user_max, listing.watchers.all(), "max not added")

    def test_can_create_bid_on_listing(self):
        listing = Listing.objects.create(title="thing", listed_by=self.user)
        Bid.objects.create(listing=listing, amount=5.00, bidder=self.user)
        self.assertEqual(listing.bids.count(), 1)

    def test_can_return_highest_bidder(self):
        user_max = create_registered_user("max")
        listing = Listing.objects.create(title="thing", listed_by=self.user)
        Bid.objects.create(listing=listing, amount=4.00, bidder=user_max)
        Bid.objects.create(listing=listing, amount=5.00, bidder=self.user)
        self.assertEqual(listing.highest_bidder, self.user)

    def test_returns_none_if_no_bidders(self):
        listing = Listing.objects.create(title="thing", listed_by=self.user)
        self.assertEqual(listing.highest_bidder, None)

    def test_price_returns_default_if_no_starting_price_or_bids(self):
        listing = Listing.objects.create(title="thing", listed_by=self.user)
        self.assertEqual(listing.price.amount, Decimal("0.00"))

    def test_price_returns_starting_bid_if_no_bids(self):
        listing = Listing.objects.create(title="thing", listed_by=self.user)
        listing.starting_bid = "4.00"
        listing.save()
        self.assertEqual(listing.price.amount, Decimal("4.00"))

    def test_price_returns_bid_over_starting_price(self):
        listing = Listing.objects.create(
            title="thing", listed_by=self.user, starting_bid="4.00"
        )
        Bid.objects.create(listing=listing, amount=5.00, bidder=self.user)
        self.assertEqual(listing.price.amount, Decimal("5.00"))

    def test_highest_bid_retuns_none_if_no_bids(self):
        listing = Listing.objects.create(title="thing", listed_by=self.user)
        self.assertIsNone(listing.highest_bid)

    def test_only_lister_can_close_listing(self):
        user_max = create_registered_user("max")
        listing = Listing.objects.create(title="thing", listed_by=self.user)
        listing.close(user_max)
        self.assertFalse(listing.closed)
        listing.close(self.user)
        self.assertTrue(listing.closed)

    def test_highest_bidder_wins_closed_listing(self):
        user_max = create_registered_user("max")
        listing = Listing.objects.create(title="thing", listed_by=self.user)
        Bid.objects.create(listing=listing, amount=4.00, bidder=user_max)
        listing.close(self.user)
        self.assertEqual(listing.winner, user_max)

    def test_returns_none_if_closed_with_no_bidders(self):
        listing = Listing.objects.create(title="thing", listed_by=self.user)
        listing.close(self.user)
        self.assertIsNone(listing.winner)

    def test_no_winner_on_open_listing(self):
        user_max = create_registered_user("max")
        listing = Listing.objects.create(title="thing", listed_by=self.user)
        Bid.objects.create(listing=listing, amount=4.00, bidder=user_max)
        self.assertIsNone(listing.winner)


class BidTest(TestCase):
    def setUp(self) -> None:
        self.user = create_registered_user("joe")
        return super().setUp()

    def test_can_create_new_bid(self):
        listing = Listing.objects.create(title="thing", listed_by=self.user)
        bid = Bid(listing=listing, amount="5.00", bidder=self.user)
        bid.full_clean()  # no raise

    def test_cannot_bid_on_closed_bid(self):
        listing = Listing.objects.create(title="thing", listed_by=self.user)
        listing.close(self.user)
        user_max = create_registered_user("max")
        bid = Bid(listing=listing, amount=4.00, bidder=user_max)
        with self.assertRaises(ValidationError):
            bid.full_clean()
        self.assertEqual(listing.bids.count(), 0)

    def test_bid_must_be_higher_than_associated_listing_starting_amount(self):
        listing = Listing.objects.create(
            title="thing", listed_by=self.user, starting_bid=5.00
        )
        bid = Bid(listing=listing, amount="4.00", bidder=self.user)
        with self.assertRaises(ValidationError):
            bid.full_clean()

    def test_bid_must_be_higher_than_other_bids_of_associated_listing(self):
        listing = Listing.objects.create(
            title="Sweet Thing", listed_by=self.user, starting_bid=5.00
        )
        Bid.objects.create(listing=listing, amount="6.00", bidder=self.user)
        bid = Bid(listing=listing, amount="5.50", bidder=self.user)
        with self.assertRaises(ValidationError):
            bid.full_clean()

    def test_cannot_place_bid_on_closed_listing(self):
        listing = Listing.objects.create(
            title="Sweet Thing", listed_by=self.user, starting_bid=5.00
        )
        listing.close(self.user)
        bid = Bid(listing=listing, amount="6.00", bidder=self.user)
        with self.assertRaises(ValidationError):
            bid.full_clean()


class CommentTest(TestCase):
    def setUp(self) -> None:
        self.user = create_registered_user("joe")
        return super().setUp()

    def test_listing_can_have_comment(self):
        listing = Listing.objects.create(
            title="Sweet Thing", listed_by=self.user, starting_bid=5.00
        )
        listing.comments.create(commenter=self.user, text="best ever")
        self.assertEqual(listing.comments.count(), 1)
