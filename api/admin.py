from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Category, Question, Match, Round, MatchHistory


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'rating', 'level', 'wins', 'losses', 'is_online')
    list_filter = ('is_online', 'is_in_game', 'level')
    search_fields = ('username', 'email')
    fieldsets = UserAdmin.fieldsets + (
        ('Game Info', {'fields': ('avatar', 'rating', 'level', 'wins', 'losses', 'is_online', 'is_in_game')}),
    )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'question_count')
    
    def question_count(self, obj):
        return obj.questions.count()
    question_count.short_description = 'Questions'


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text_preview', 'category', 'difficulty', 'correct_option')
    list_filter = ('category', 'difficulty')
    search_fields = ('text',)
    
    def text_preview(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_preview.short_description = 'Question'


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'player1', 'player2', 'score1', 'score2', 'winner', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('player1__username', 'player2__username')


@admin.register(Round)
class RoundAdmin(admin.ModelAdmin):
    list_display = ('match', 'round_number', 'question', 'player1_score', 'player2_score')
    list_filter = ('match',)


@admin.register(MatchHistory)
class MatchHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'opponent', 'user_score', 'opponent_score', 'is_winner', 'rating_change', 'created_at')
    list_filter = ('is_winner', 'created_at')
    search_fields = ('user__username', 'opponent__username')

