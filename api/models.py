from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Custom User model with game-related fields"""
    avatar = models.URLField(max_length=500, null=True, blank=True)  # Changed to URLField for Google avatar
    rating = models.IntegerField(default=1000)
    level = models.IntegerField(default=1)
    wins = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    is_online = models.BooleanField(default=False)
    is_in_game = models.BooleanField(default=False)
    google_id = models.CharField(max_length=100, null=True, blank=True, unique=True)  # Google OAuth ID
    
    def __str__(self):
        return self.username
    
    def update_rating(self, won: bool):
        """Update user rating after a match"""
        if won:
            self.rating += 20
            self.wins += 1
        else:
            self.rating = max(0, self.rating - 15)
            self.losses += 1
        
        # Update level based on rating
        self.level = (self.rating // 200) + 1
        self.save()
    
    @property
    def total_matches(self):
        return self.wins + self.losses
    
    @property
    def win_rate(self):
        if self.total_matches == 0:
            return 0
        return round((self.wins / self.total_matches) * 100, 1)


class Category(models.Model):
    """Question categories"""
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, blank=True)  # Emoji or icon name
    
    class Meta:
        verbose_name_plural = "Categories"
    
    def __str__(self):
        return self.name


class Question(models.Model):
    """Quiz questions"""
    text = models.TextField()
    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255)
    option_d = models.CharField(max_length=255)
    correct_option = models.CharField(
        max_length=1,
        choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D')]
    )
    explanation = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='questions')
    difficulty = models.IntegerField(default=1, choices=[(1, 'Easy'), (2, 'Medium'), (3, 'Hard')])
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.text[:50]
    
    def get_options(self):
        return {
            'A': self.option_a,
            'B': self.option_b,
            'C': self.option_c,
            'D': self.option_d,
        }


class Match(models.Model):
    """Game match between two players"""
    STATUS_CHOICES = [
        ('waiting', 'Waiting'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    player1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='matches_as_player1')
    player2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='matches_as_player2', null=True, blank=True)
    score1 = models.IntegerField(default=0)
    score2 = models.IntegerField(default=0)
    winner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='won_matches')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    current_round = models.IntegerField(default=0)
    total_rounds = models.IntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        p2_name = self.player2.username if self.player2 else "Waiting..."
        return f"{self.player1.username} vs {p2_name}"
    
    def get_questions(self):
        """Get all questions for this match"""
        return [round.question for round in self.rounds.all().order_by('round_number')]


class Round(models.Model):
    """Individual round within a match"""
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='rounds')
    round_number = models.IntegerField()
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    player1_answer = models.CharField(max_length=1, null=True, blank=True)
    player2_answer = models.CharField(max_length=1, null=True, blank=True)
    player1_time = models.FloatField(null=True, blank=True)  # Time in seconds
    player2_time = models.FloatField(null=True, blank=True)
    player1_score = models.IntegerField(default=0)
    player2_score = models.IntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['match', 'round_number']
        ordering = ['round_number']
    
    def __str__(self):
        return f"Match {self.match.id} - Round {self.round_number}"
    
    def calculate_score(self, time_taken: float, is_correct: bool) -> int:
        """Calculate score based on answer time"""
        if not is_correct:
            return 0
        if time_taken <= 3:
            return 100
        elif time_taken <= 7:
            return 70
        else:
            return 40


class MatchHistory(models.Model):
    """Detailed match history for users"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='match_history')
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    opponent = models.ForeignKey(User, on_delete=models.CASCADE, related_name='opponent_history')
    user_score = models.IntegerField()
    opponent_score = models.IntegerField()
    is_winner = models.BooleanField()
    rating_change = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Match histories"
        ordering = ['-created_at']
    
    def __str__(self):
        result = "Won" if self.is_winner else "Lost"
        return f"{self.user.username} {result} vs {self.opponent.username}"

