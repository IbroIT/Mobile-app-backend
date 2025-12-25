from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    RegisterView, ProfileView, UserDetailView, LeaderboardView,
    CategoryListView, RandomQuestionsView, MatchHistoryView,
    MatchDetailView, user_stats, guest_login,
    generate_ai_questions, start_offline_game, finish_offline_game,
    google_auth
)

urlpatterns = [
    # Auth endpoints
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/guest/', guest_login, name='guest_login'),
    path('auth/google/', google_auth, name='google_auth'),
    
    # Profile endpoints
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/stats/', user_stats, name='user_stats'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user_detail'),
    path('leaderboard/', LeaderboardView.as_view(), name='leaderboard'),
    
    # Game endpoints
    path('categories/', CategoryListView.as_view(), name='categories'),
    path('questions/random/', RandomQuestionsView.as_view(), name='random_questions'),
    path('questions/generate/', generate_ai_questions, name='generate_ai_questions'),
    
    # Offline game endpoints
    path('game/offline/start/', start_offline_game, name='start_offline_game'),
    path('game/offline/finish/', finish_offline_game, name='finish_offline_game'),
    
    # Match endpoints
    path('matches/history/', MatchHistoryView.as_view(), name='match_history'),
    path('matches/<int:pk>/', MatchDetailView.as_view(), name='match_detail'),
]
