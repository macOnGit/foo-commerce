from django.test import TestCase
from auctions.forms import ListingForm


class ListingFormTest(TestCase):
    def test_form_bid_amount_input_has_placeholder(self):
        form = ListingForm()
        self.assertIn('placeholder="Bid"', form.as_p())

    def test_form_comment_input_has_placeholder(self):
        form = ListingForm()
        self.assertIn('placeholder="Comment"', form.as_p())
