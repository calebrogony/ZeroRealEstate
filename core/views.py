from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import JsonResponse
from decimal import Decimal, InvalidOperation
from .forms import CustomUserCreationForm
from .forms import CustomUserCreationForm, MessageForm
from .models import Property, Investment, Clan, Wallet, Message, LedgerEntry
from django.contrib import messages
from django.core.mail import send_mail


# Register View
def register_view(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # log them in immediately
            return redirect("dashboard")  # change "dashboard" to your actual route name
    else:
        form = CustomUserCreationForm()
    return render(request, "register.html", {"form": form})

# Login View
def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("dashboard")
    else:
        form = AuthenticationForm()
    return render(request, "login.html", {"form": form})

# Logout View
def logout_view(request):
    logout(request)
    return redirect("login")


def forgot_password(request):
    if request.method == "POST":
        username = request.POST.get("username")
        try:
            user = User.objects.get(username=username)
            request.session["reset_user_id"] = user.id
            return redirect("verify_account")
        except User.DoesNotExist:
            messages.error(request, "Account not found.")
    return render(request, "forgot_password.html")


def verify_account(request):
    user_id = request.session.get("reset_user_id")
    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        entered_phone = request.POST.get("phone")
        if user.profile.phone == entered_phone:  # Example check
            return redirect("reset_password")
        else:
            messages.error(request, "Verification failed.")
    return render(request, "verify_account.html")


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import update_session_auth_hash

User = get_user_model()

from django.shortcuts import render, redirect
from django.contrib import messages
from .models import RecoveryRequest

def reset_password(request):
    verified = request.session.get("verified", False)

    if request.method == "POST":
        if not verified:
            # First step: collect verification details
            id_number = request.POST.get("id_number")
            mobile_number = request.POST.get("mobile_number")
            email = request.POST.get("email")

            # Save to DB for admin review
            RecoveryRequest.objects.create(
                id_number=id_number,
                mobile_number=mobile_number,
                email=email
            )

            # Mark session as verified so template shows "await call"
            request.session["verified"] = True
            messages.success(request, "Verification submitted. Await call from agent within 10 minutes.")
        else:
            # Later you can add actual password reset logic here
            messages.info(request, "Please await agent verification before resetting password.")

    return render(request, "reset_password.html", {"verified": request.session.get("verified", False)})


# ==========================
# DASHBOARD
# ==========================
from decimal import Decimal
from django.db.models import Sum
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Wallet, Investment, Property, User, Staff  # include Staff if you want staff count

@login_required
def dashboard(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)

    # Investor stats (per user)
    investments = Investment.objects.filter(user=request.user)
    total_shares = investments.aggregate(Sum("shares_bought"))["shares_bought__sum"] or 0
    total_invested = investments.aggregate(Sum("total_invested"))["total_invested__sum"] or 0
    monthly_income = sum(inv.monthly_income for inv in investments)

    user_clan = request.user.clans.first()  # or via ClanMembership

    # Platform stats (global)
    properties_count = Property.objects.filter(approved=True, available_shares__gt=0).count()
    investors_count = User.objects.filter(investment__isnull=False).distinct().count()

    # Sum of all investors' contributions

    investor_total = Investment.objects.aggregate(total=Sum("total_invested"))["total"] or Decimal(0)
    total_capital = investor_total * Decimal("1.75")

    # Apply formula: +75% of that total

    investor_total = Investment.objects.aggregate(Sum("total_invested"))["total_invested__sum"] or Decimal(0)
    total_capital = investor_total * Decimal("1.75")

    # Optional: staff count
    staff_count = Staff.objects.count() if 'Staff' in globals() else 0

    # Inbox messages
    inbox_messages = request.user.received_messages.all()

    return render(request, "dashboard.html", {
        "user": request.user,
        "wallet": wallet,
        "total_shares": total_shares,
        "total_invested": total_invested,
        "monthly_income": monthly_income,
        "properties_count": properties_count,
        "investors_count": investors_count,
        "total_capital": total_capital,
        "staff_count": staff_count,
        "inbox_messages": inbox_messages,
        "user_clan": user_clan,
    })


@login_required
def profile(request):
    investments = Investment.objects.filter(user=request.user)

    total_shares = investments.aggregate(Sum("shares_bought"))["shares_bought__sum"] or 0
    total_invested = investments.aggregate(Sum("total_invested"))["total_invested__sum"] or Decimal("0.00")

    try:
        monthly_income = sum(inv.monthly_income for inv in investments)
    except (TypeError, ValueError, InvalidOperation):
        monthly_income = Decimal("0.00")

    user_clan = request.user.clans.first()
    wallet, _ = Wallet.objects.get_or_create(user=request.user)

    context = {
        "total_shares": total_shares,
        "total_invested": total_invested,
        "monthly_income": monthly_income,
        "user_clan": user_clan,
        "wallet": wallet,
        "user": request.user,
    }
    return render(request, "profile.html", context)


# ==========================
# LISTINGS
# ==========================

@login_required
def listings(request):
    properties = Property.objects.filter(approved=True)
    return render(request, "listings.html", {"properties": properties})


# ==========================
# BUY SHARES
# ==========================
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.core.exceptions import ValidationError

from .models import Property, Wallet, Investment, Message
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import Wallet, Property, Investment, LedgerEntry

@login_required
def buy_shares(request, property_id):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    property_obj = get_object_or_404(Property, id=property_id)

    if request.method == "POST":
        try:
            shares = int(request.POST.get("shares", "0"))
        except (TypeError, ValueError):
            messages.error(request, "Invalid number of shares.")
            return redirect("listings")

        if shares <= 0:
            messages.error(request, "You must buy at least 1 share.")
            return redirect("listings")

        if shares > property_obj.available_shares:
            messages.error(request, "Not enough shares available.")
            return redirect("listings")

        amount = Decimal(shares) * property_obj.price_per_share
        fee = amount * Decimal("0.02")

        if wallet.balance < (amount + fee):
            messages.error(request, "Insufficient wallet balance.")
            return redirect("listings")

        # Deduct from wallet
        wallet.balance -= (amount + fee)
        wallet.save()

        # Deduct shares from property pool (only once!)
        property_obj.available_shares -= shares
        property_obj.save()

        # Update or create investment record
        investment, created = Investment.objects.get_or_create(
            user=request.user,
            property_obj=property_obj,
            defaults={"shares_bought": 0, "total_invested": 0}
        )
        investment.shares_bought += shares
        investment.total_invested = investment.shares_bought * property_obj.price_per_share
        investment.save()

        # Record transaction
        LedgerEntry.objects.create(
            user=request.user,
            wallet=wallet,
            transaction_type="BUY",
            amount=amount,
            fee=fee,
            description=f"Bought {shares} shares in {property_obj.name}"
        )

        messages.success(request, f"Successfully bought {shares} shares.")

    return redirect("portfolio")
# PRESTIGE
# ==========================
@login_required
def prestige(request):
    user = request.user
    investments = Investment.objects.filter(user=user)

    total_invested = sum(inv.total_invested for inv in investments)
    monthly_income = sum(inv.monthly_income for inv in investments)
    user_clan = user.clans.first()

    # Prestige thresholds
    thresholds = [1000, 5000, 10000, 20000, 50000, 100000]
    perks = {
        1: "Bronze → Basic dashboard access",
        2: "Silver → Unlocks advanced portfolio analytics",
        3: "Gold → Eligible for clan leadership and community perks",
        4: "Platinum → Priority access to new listings",
        5: "Emerald → Enhanced wallet features",
        6: "Ruby → VIP community recognition",
        7: "Diamond → Black Card + premium listings",
    }

    prestige_level = 1
    next_threshold = None
    next_unlock = None

    for i, t in enumerate(thresholds, start=1):
        if total_invested < t:
            prestige_level = i
            next_threshold = t
            next_unlock = perks.get(i+1)
            break
    else:
        prestige_level = len(thresholds) + 1
        next_threshold = None
        next_unlock = None

    # Progress percentage
    if next_threshold:
        prev_threshold = thresholds[prestige_level - 2] if prestige_level > 1 else 0
        prestige_progress = int(((total_invested - prev_threshold) / (next_threshold - prev_threshold)) * 100)
    else:
        prestige_progress = 100

    levels = range(1, len(thresholds) + 2)

    return render(request, "prestige.html", {
        "user": user,
        "prestige_level": prestige_level,
        "total_invested": total_invested,
        "monthly_income": monthly_income,
        "user_clan": user_clan,
        "levels": levels,
        "prestige_progress": prestige_progress,
        "next_threshold": next_threshold,
        "next_unlock": next_unlock,
        "perks": perks,
    })



@login_required
def platform_stats(request):
    total_properties = Property.objects.filter(approved=True, available_shares__gt=0).count()
    total_investors = User.objects.filter(investment__isnull=False).distinct().count()
    total_capital = Investment.objects.aggregate(Sum("total_invested"))["total_invested__sum"] or 0

    return render(request, "platform_stats.html", {
        "total_properties": total_properties,
        "total_investors": total_investors,
        "total_capital": total_capital,
    })



# ==========================
# COMMUNITY / CLANS
# ==========================

@login_required
def community(request):
    clans = Clan.objects.all()
    return render(request, "community.html", {"clans": clans})


@login_required
def create_clan(request):
    if request.method == "POST":
        # Check if user already owns a clan
        if Clan.objects.filter(leader=request.user).exists():
            messages.error(request, "You can only create one clan.")
            return redirect("community")

        # Check if user is already a member of any clan
        if Clan.objects.filter(members=request.user).exists():
            messages.error(request, "You are already in a clan.")
            return redirect("community")

        name = request.POST.get("name")
        clan = Clan.objects.create(name=name, leader=request.user)
        clan.members.add(request.user)
        messages.success(request, "Clan created successfully!")
        return redirect("community")

    return render(request, "create_clan.html")


@login_required
def join_clan(request, clan_id):
    clan = get_object_or_404(Clan, id=clan_id)
    existing_clan = Clan.objects.filter(members=request.user).first()
    if not existing_clan:
        clan.members.add(request.user)
    return redirect("community")


# ==========================
# WALLET
# ==========================

@login_required
def wallet(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    transactions = LedgerEntry.objects.filter(user=request.user).order_by("-created_at")

    return render(request, "wallet.html", {
        "wallet": wallet,
        "transactions": transactions,
    })


# ==========================
# ABOUT
# ==========================

from django.shortcuts import render
from .models import Staff
@login_required
def about(request):
    staff_members = Staff.objects.all()
    return render(request, "about.html", {
        "staff_members": staff_members,
    })

# ==========================
# PORTFOLIO
# ==========================

@login_required
def portfolio(request):
    investments = Investment.objects.filter(user=request.user)

    total_shares = investments.aggregate(Sum("shares_bought"))["shares_bought__sum"] or 0
    total_invested = investments.aggregate(Sum("total_invested"))["total_invested__sum"] or Decimal("0.00")

    try:
        monthly_income = sum(inv.monthly_income for inv in investments)
    except (TypeError, ValueError, InvalidOperation):
        monthly_income = Decimal("0.00")

    user_clan = request.user.clans.first()
    wallet, _ = Wallet.objects.get_or_create(user=request.user)

    context = {
        "investments": investments,
        "user_clan": user_clan,
        "total_shares": total_shares,
        "total_invested": total_invested,
        "monthly_income": monthly_income,
        "wallet": wallet,
        "user": request.user,
    }
    return render(request, "portfolio.html", context)


# ==========================
# USER STATS (AJAX)
# ==========================

@login_required
def user_stats(request):
    investments = Investment.objects.filter(user=request.user)

    total_shares = investments.aggregate(Sum("shares_bought"))["shares_bought__sum"] or 0
    total_value = investments.aggregate(Sum("total_invested"))["total_invested__sum"] or Decimal("0.00")

    try:
        monthly_income = sum(inv.monthly_income for inv in investments)
    except (TypeError, ValueError, InvalidOperation):
        monthly_income = Decimal("0.00")

    data = {
        "total_shares": total_shares,
        "total_value": float(total_value),
        "monthly_income": float(monthly_income),
        "prestige_level": request.user.prestige_level,
        "equity_percentage": request.user.equity_percentage,
    }
    return JsonResponse(data)


# ==========================
# DEPOSIT
# ==========================


@login_required
def deposit(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)

    if request.method == "POST":
        deposit_amount = Decimal(request.POST.get("amount", "0.00"))

        if deposit_amount > 0:
            wallet.balance += deposit_amount
            wallet.save()

            # ✅ Ledger entry for deposit
            LedgerEntry.objects.create(
                user=request.user,
                wallet=wallet,
                transaction_type="DEPOSIT",
                amount=deposit_amount,
                description="User deposited funds"
            )

            messages.success(request, "Deposit successful!")
        else:
            messages.error(request, "Deposit amount must be greater than zero.")

    # ✅ Render deposit.html instead of redirect
    return render(request, "deposit.html", {"wallet": wallet})



# ==========================
# WITHDRAW
# ==========================

@login_required
def withdraw(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)

    if request.method == "POST":
        withdraw_amount = Decimal(request.POST.get("amount", "0.00"))
        if withdraw_amount > 0 and wallet.balance >= withdraw_amount:
            fee_percent = Decimal("0.02")
            fee_amount = withdraw_amount * fee_percent

            # Deduct amount + fee
            wallet.balance -= (withdraw_amount + fee_amount)
            wallet.save()

            # Ledger entry
            LedgerEntry.objects.create(
                user=request.user,
                wallet=wallet,
                transaction_type="WITHDRAW",
                amount=withdraw_amount,
                fee=fee_amount,
                description="User withdrew funds"
            )

            messages.success(request, "Withdrawal successful!")
        else:
            messages.error(request, "Invalid amount or insufficient balance.")

    return render(request, "withdraw.html", {"wallet": wallet})

from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import Wallet, Investment, LedgerEntry

@login_required
def liquidate(request, investment_id):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    investment = get_object_or_404(Investment, id=investment_id, user=request.user)

    if request.method == "POST":
        try:
            shares_to_sell = int(request.POST.get("shares", 0))
        except (TypeError, ValueError):
            messages.error(request, "Invalid number of shares entered.")
            return redirect("portfolio")

        if shares_to_sell <= 0:
            messages.error(request, "You must sell at least 1 share.")
            return redirect("portfolio")

        if shares_to_sell > investment.shares_bought:
            messages.error(request, "You cannot sell more shares than you own.")
            return redirect("portfolio")

        # Calculate sale amount and fee
        amount = shares_to_sell * investment.property_obj.price_per_share
        fee = amount * Decimal("0.02")

        # Update wallet balance
        wallet.balance += (amount - fee)
        wallet.save()

        # Return shares to property pool
        investment.property_obj.available_shares += shares_to_sell
        investment.property_obj.save()

        # Update or delete investment record
        investment.shares_bought -= shares_to_sell
        if investment.shares_bought <= 0:
            # Delete the investment if no shares remain
            investment.delete()
        else:
            investment.total_invested = investment.shares_bought * investment.property_obj.price_per_share
            investment.save()

        # Record transaction in ledger
        LedgerEntry.objects.create(
            user=request.user,
            wallet=wallet,
            transaction_type="SELL",
            amount=amount,
            fee=fee,
            description=f"Sold {shares_to_sell} shares in {investment.property_obj.name}"
        )

        messages.success(request, f"Successfully sold {shares_to_sell} shares.")

    return redirect("portfolio")


@login_required
def add_listing(request):
    if request.method == "POST":
        name = request.POST['name']
        location = request.POST['location']
        description = request.POST['description']
        price_per_share = request.POST['price_per_share']
        available_shares = request.POST['available_shares']
        total_shares = request.POST['total_shares']
        dividend_rate = request.POST['monthly_dividend_per_share']

        Property.objects.create(
            name=name,
            location=location,
            description=description,
            price_per_share=price_per_share,
            available_shares=available_shares,
            total_shares=total_shares,
            monthly_dividend_per_share=dividend_rate,
            approved=False,
            created_by=request.user  # ✅ this fixes the error
        )

        messages.success(request, "Listing submitted successfully. Awaiting admin approval.")
        return redirect('listings')

    return redirect('listings')

from .forms import ContactForm


@login_required
def contact_us(request):
    if request.method == "POST":
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.sender = request.user
            message.sender_type = "user"
            message.save()
            messages.success(request, "Your message has been sent.")
            return redirect("inbox")   # <-- redirect to inbox
    else:
        form = MessageForm()
    return render(request, "contact.html", {"form": form})

from .models import VerifyTransaction

@login_required
def verify_transaction(request):
    if request.method == "POST":
        transaction_id = request.POST.get("transaction_id")
        notes = request.POST.get("notes", "")

        VerifyTransaction.objects.create(
            user=request.user,
            transaction_id=transaction_id,
            notes=notes
        )

        messages.success(request, "Transaction submitted for verification.")
        return redirect("deposit")  # back to deposit page

    return redirect("deposit")
from .forms import ContactForm

@login_required
def contact_us(request):
    if request.method == "POST":
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.sender = request.user          # set sender to current user
            message.sender_type = "user"           # optional: mark sender type
            message.save()
            messages.success(request, "Your message has been sent.")
            return redirect("inbox")               # redirect to inbox page
    else:
        form = MessageForm()

    return render(request, "contact.html", {"form": form})

@login_required
def inbox(request):
    received_messages = Message.objects.filter(recipient=request.user).order_by("-created_at")
    sent_messages = Message.objects.filter(sender=request.user).order_by("-created_at")

    form = MessageForm()  # blank form for sending new messages

    return render(request, "inbox.html", {
        "received_messages": received_messages,
        "sent_messages": sent_messages,
        "form": form,
    })


@login_required
def reply(request, message_id):
    original = get_object_or_404(Message, id=message_id, recipient=request.user)
    if request.method == "POST":
        reply_msg = Message(
            sender=request.user,
            sender_type="user",
            recipient=original.sender,
            subject="Re: " + original.subject,
            body="(write your reply here)"  # you can extend with a form
        )
        reply_msg.save()
        messages.success(request, "Reply sent.")
        return redirect("inbox")


