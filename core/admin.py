from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model
from .models import Property, Investment, Clan, Wallet, LedgerEntry, VerifyTransaction, Message, Staff

User = get_user_model()

# Branding for Admin
admin.site.site_header = "Zero Real Estate Administration"
admin.site.site_title = "Zero RE Control Panel"
admin.site.index_title = "Business Command Center"

# Property
@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'total_value', 'price_per_share', 'available_shares', 'approved')

# Investment
@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'property_obj', 'shares_bought', 'total_invested', 'date_invested')

# Clan
@admin.register(Clan)
class ClanAdmin(admin.ModelAdmin):
    list_display = ('name', 'leader')

# Wallet
@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance')

# Ledger Entry
@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ('user', 'transaction_type', 'amount', 'created_at')

# Verify Transaction
@admin.register(VerifyTransaction)
class VerifyTransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'user', 'verified', 'created_at')

# Staff
@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ("full_name", "role", "hired_date")
    search_fields = ("full_name", "role")

# Message
@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("sender_type", "sender", "recipient", "subject", "created_at", "is_read")
    list_filter = ("sender_type", "is_read")
    search_fields = ("subject", "body", "sender__username", "recipient__username")

# Custom User
admin.site.register(User, UserAdmin)
