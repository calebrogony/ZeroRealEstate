from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.db.models import Sum, Max
from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError

# ==============================
# Custom User Model
# ==============================
class User(AbstractUser):
    equity_percentage = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    prestige_level = models.IntegerField(default=0)

    def update_equity_and_prestige(self):
        investments = Investment.objects.filter(user=self)

        total_invested = investments.aggregate(
            Sum("total_invested")
        )["total_invested__sum"] or Decimal("0.00")

        # Base prestige level
        if total_invested >= 1_000_000:
            base_level = 5
        elif total_invested >= 200_000:
            base_level = 4
        elif total_invested >= 50_000:
            base_level = 3
        elif total_invested >= 10_000:
            base_level = 2
        else:
            base_level = 1

        # Tier bonus based on highest share price
        highest_price = investments.aggregate(
            Max("property_obj__price_per_share")
        )["property_obj__price_per_share__max"] or Decimal("0.00")

        if highest_price >= 100_000:
            bonus = 2
        elif highest_price >= 50_000:
            bonus = 1
        else:
            bonus = 0

        final_level = min(base_level + bonus, 7)

        self.prestige_level = final_level
        self.equity_percentage = total_invested / Decimal("1000")
        self.save()


# ==============================
# Property Model
# ==============================
from decimal import Decimal
from django.conf import settings
from django.db import models

class Property(models.Model):
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=200)
    description = models.TextField()

    price_per_share = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_shares = models.IntegerField()
    available_shares = models.IntegerField()

    total_value = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    monthly_dividend_per_share = models.DecimalField(max_digits=6, decimal_places=4, default=Decimal("0.00"))

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    approved = models.BooleanField(default=False)

    # New fields for images
    image1 = models.ImageField(upload_to="property_images/", blank=True, null=True)
    image2 = models.ImageField(upload_to="property_images/", blank=True, null=True)
    image3 = models.ImageField(upload_to="property_images/", blank=True, null=True)

    def __str__(self):
        return self.name


# ==============================
# Investment Model
# ==============================
class Investment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    property_obj = models.ForeignKey("Property", on_delete=models.CASCADE)

    shares_bought = models.IntegerField()
    total_invested = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    date_invested = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        price = Decimal(str(self.property_obj.price_per_share or "0.00"))
        self.total_invested = Decimal(self.shares_bought or 0) * price
        super().save(*args, **kwargs)

        if is_new:
            self.property_obj.available_shares -= self.shares_bought
            self.property_obj.save()

        total_property = Investment.objects.filter(property_obj=self.property_obj).aggregate(
            Sum("total_invested")
        )["total_invested__sum"] or Decimal("0.00")

        self.property_obj.total_value = total_property
        self.property_obj.save()

        self.user.update_equity_and_prestige()

    @property
    def monthly_income(self):
        try:
            price = Decimal(str(self.property_obj.price_per_share or "0.00"))
            rate = Decimal(str(self.property_obj.monthly_dividend_per_share or "0.00"))
            shares = Decimal(str(self.shares_bought or 0))
            return shares * (price * rate)
        except (InvalidOperation, TypeError, ValueError):
            return Decimal("0.00")


# ==============================
# Clan Model
# ==============================
class Clan(models.Model):
    name = models.CharField(max_length=100, unique=True)
    leader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='led_clans',
        null=True,
        blank=True
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='clans'
    )

    def __str__(self):
        return self.name


# ==============================
# Wallet Model
# ==============================
class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    def deduct(self, amount):
        if amount <= 0:
            raise ValidationError("Amount must be positive.")
        if self.balance < amount:
            raise ValidationError("Insufficient balance.")
        self.balance -= amount
        self.save()

    def can_purchase(self, amount):
        return self.balance >= amount and self.balance > 0

    def __str__(self):
        return f"{self.user.username}'s wallet"


# ==============================
# Ledger Entry Model
# ==============================
class LedgerEntry(models.Model):
    TRANSACTION_TYPES = [
        ("BUY", "Buy"),
        ("SELL", "Sell"),
        ("DEPOSIT", "Deposit"),
        ("WITHDRAW", "Withdraw"),
        ("ALLOCATE", "Admin Allocation"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, null=True, blank=True)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.transaction_type} - {self.amount} (Fee: {self.fee})"


# ==============================
# Verify Transaction Model
# ==============================
class VerifyTransaction(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    transaction_id = models.CharField(max_length=50, unique=True)
    notes = models.TextField(blank=True)
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_id} - {self.user.username}"


# ==============================
# Message Model
# ==============================
class Message(models.Model):
    SENDER_TYPES = [
        ("user", "User"),
        ("admin", "Admin"),
    ]

    sender_type = models.CharField(max_length=10, choices=SENDER_TYPES)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_messages", null=True, blank=True)

    subject = models.CharField(max_length=255)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.sender_type.capitalize()} message: {self.subject}"
from django.db import models

from django.db import models

class Staff(models.Model):
    full_name = models.CharField(max_length=150)
    role = models.CharField(max_length=100, blank=True, null=True)
    hired_date = models.DateField(blank=True, null=True)

    # New fields for About Us
    photo = models.ImageField(upload_to="staff_photos/", blank=True, null=True)
    portfolio_summary = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.full_name
