from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import Question, Category, Match, Round, MatchHistory

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password2')
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Passwords don't match"})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user profile"""
    total_matches = serializers.IntegerField(read_only=True)
    win_rate = serializers.FloatField(read_only=True)
    
    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'avatar', 'rating', 'level',
            'wins', 'losses', 'total_matches', 'win_rate', 'is_online'
        )
        read_only_fields = ('rating', 'level', 'wins', 'losses', 'is_online')


class UserPublicSerializer(serializers.ModelSerializer):
    """Serializer for public user info (opponent)"""
    class Meta:
        model = User
        fields = ('id', 'username', 'avatar', 'rating', 'level', 'wins', 'losses')


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for question categories"""
    question_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ('id', 'name', 'icon', 'question_count')
    
    def get_question_count(self, obj):
        return obj.questions.count()


class QuestionSerializer(serializers.ModelSerializer):
    """Serializer for questions"""
    options = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Question
        fields = ('id', 'text', 'options', 'category', 'category_name', 'difficulty')
    
    def get_options(self, obj):
        return {
            'A': obj.option_a,
            'B': obj.option_b,
            'C': obj.option_c,
            'D': obj.option_d,
        }


class QuestionWithAnswerSerializer(QuestionSerializer):
    """Serializer for questions with correct answer (for review)"""
    class Meta(QuestionSerializer.Meta):
        fields = QuestionSerializer.Meta.fields + ('correct_option', 'explanation')


class RoundSerializer(serializers.ModelSerializer):
    """Serializer for match rounds"""
    question = QuestionSerializer(read_only=True)
    
    class Meta:
        model = Round
        fields = (
            'id', 'round_number', 'question', 'player1_answer', 'player2_answer',
            'player1_time', 'player2_time', 'player1_score', 'player2_score'
        )


class RoundDetailSerializer(serializers.ModelSerializer):
    """Serializer for round details with correct answers"""
    question = QuestionWithAnswerSerializer(read_only=True)
    
    class Meta:
        model = Round
        fields = (
            'id', 'round_number', 'question', 'player1_answer', 'player2_answer',
            'player1_time', 'player2_time', 'player1_score', 'player2_score'
        )


class MatchSerializer(serializers.ModelSerializer):
    """Serializer for matches"""
    player1 = UserPublicSerializer(read_only=True)
    player2 = UserPublicSerializer(read_only=True)
    winner = UserPublicSerializer(read_only=True)
    
    class Meta:
        model = Match
        fields = (
            'id', 'player1', 'player2', 'score1', 'score2', 'winner',
            'status', 'current_round', 'total_rounds', 'created_at',
            'started_at', 'ended_at'
        )


class MatchDetailSerializer(MatchSerializer):
    """Serializer for match details with rounds"""
    rounds = RoundDetailSerializer(many=True, read_only=True)
    
    class Meta(MatchSerializer.Meta):
        fields = MatchSerializer.Meta.fields + ('rounds',)


class MatchHistorySerializer(serializers.ModelSerializer):
    """Serializer for match history"""
    opponent = UserPublicSerializer(read_only=True)
    
    class Meta:
        model = MatchHistory
        fields = (
            'id', 'match', 'opponent', 'user_score', 'opponent_score',
            'is_winner', 'rating_change', 'created_at'
        )
