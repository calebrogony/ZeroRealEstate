from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    # Authentication
    path('', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Password Reset (use one consistent set)
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='password_reset.html'), name='password_reset'),
    path('password_reset_done/', auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset_done/', auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'), name='password_reset_complete'),

    # Core Views
    path('dashboard/', views.dashboard, name='dashboard'),
    path('portfolio/', views.portfolio, name='portfolio'),
    path('listings/', views.listings, name='listings'),
    path('prestige/', views.prestige, name='prestige'),
    path('community/', views.community, name='community'),
    path('about/', views.about, name='about'),

    # Investment & Wallet
    path('buy/<int:property_id>/', views.buy_shares, name='buy_shares'),
    path('liquidate/<int:investment_id>/', views.liquidate, name='liquidate'),
    path('wallet/', views.wallet, name='wallet'),
    path('deposit/', views.deposit, name='deposit'),
    path('withdraw/', views.withdraw, name='withdraw'),
    path('verify-transaction/', views.verify_transaction, name='verify_transaction'),

    # Clans
    path('clan/create/', views.create_clan, name='create_clan'),
    path('clan/join/<int:clan_id>/', views.join_clan, name='join_clan'),

    # Misc
    path('add-listing/', views.add_listing, name='add_listing'),
    path('api/user-stats/', views.user_stats, name='user_stats'),
    path('contact/', views.contact_us, name='contact_us'),
    path('inbox/', views.inbox, name='inbox'),
    path("contact/", views.contact_us, name="contact"),
path("reply/<int:message_id>/", views.reply, name="reply"),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

