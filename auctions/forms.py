from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from djmoney.money import Money
from auctions.models import Listing
from decimal import InvalidOperation
from django.core.exceptions import ValidationError


class CreateListingForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.add_input(Submit("submit", "Submit"))

    class Meta:
        model = Listing
        fields = ["title", "description", "starting_bid", "image_url", "category"]

    def clean_starting_bid(self):
        # https://docs.djangoproject.com/en/3.2/ref/forms/validation/
        # #cleaning-a-specific-field-attribute
        starting_bid = self.data.get("starting_bid")
        currency = self.data.get("currency")
        money = None
        if starting_bid and currency:
            try:
                # NOTE: this creates two fields
                money = Money(starting_bid, currency)
            except InvalidOperation as e:
                raise ValidationError("Invalid starting bid") from e
        return money


class ListingForm(forms.Form):
    amount = forms.DecimalField(
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(
            attrs={
                "placeholder": "Bid",
                "class": "form-control",
            }
        ),
    )
    comment = forms.CharField(
        required=False,
        widget=forms.fields.TextInput(
            attrs={"placeholder": "Comment", "class": "form-control"}
        ),
    )
