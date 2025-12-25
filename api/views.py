from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from django.conf import settings
import random
import requests

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from .models import Question, Category, Match, MatchHistory, Round
from .serializers import (
    UserRegistrationSerializer, UserSerializer, UserPublicSerializer,
    QuestionSerializer, QuestionWithAnswerSerializer, CategorySerializer,
    MatchSerializer, MatchDetailSerializer, MatchHistorySerializer
)
from .services.gemini_service import gemini_service

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """User registration endpoint"""
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = UserRegistrationSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate tokens for the new user
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)


class ProfileView(generics.RetrieveUpdateAPIView):
    """Get or update user profile"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class UserDetailView(generics.RetrieveAPIView):
    """Get public user info by ID"""
    queryset = User.objects.all()
    serializer_class = UserPublicSerializer
    permission_classes = [permissions.IsAuthenticated]


class LeaderboardView(generics.ListAPIView):
    """Get top users by rating"""
    serializer_class = UserPublicSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return User.objects.order_by('-rating')[:50]


class CategoryListView(generics.ListAPIView):
    """List all question categories"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]


class RandomQuestionsView(APIView):
    """Get random questions for a match"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        count = int(request.query_params.get('count', 5))
        category_id = request.query_params.get('category')
        
        queryset = Question.objects.all()
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        questions = queryset.order_by('?')[:count]
        serializer = QuestionSerializer(questions, many=True)
        return Response(serializer.data)


class MatchHistoryView(generics.ListAPIView):
    """Get user's match history"""
    serializer_class = MatchHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return MatchHistory.objects.filter(user=self.request.user)


class MatchDetailView(generics.RetrieveAPIView):
    """Get match details with rounds"""
    serializer_class = MatchDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        return Match.objects.filter(Q(player1=user) | Q(player2=user))


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_stats(request):
    """Get detailed user statistics"""
    user = request.user
    
    # Recent matches
    recent_matches = MatchHistory.objects.filter(user=user)[:10]
    
    # Calculate streak
    streak = 0
    for match in recent_matches:
        if match.is_winner:
            streak += 1
        else:
            break
    
    return Response({
        'user': UserSerializer(user).data,
        'current_streak': streak,
        'recent_matches': MatchHistorySerializer(recent_matches, many=True).data,
    })


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def guest_login(request):
    """Create a guest user and return tokens"""
    import uuid
    
    # Generate unique guest username
    guest_name = f"Guest_{uuid.uuid4().hex[:8]}"
    
    # Create guest user
    user = User.objects.create_user(
        username=guest_name,
        password=uuid.uuid4().hex,
    )
    
    # Generate tokens
    refresh = RefreshToken.for_user(user)
    
    return Response({
        'user': UserSerializer(user).data,
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }, status=status.HTTP_201_CREATED)


# ============ AI Questions ============

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def generate_ai_questions(request):
    """Generate questions using Gemini AI"""
    category = request.data.get('category', 'general')
    count = int(request.data.get('count', 5))
    difficulty = request.data.get('difficulty', 'medium')
    language = request.data.get('language', 'ru')
    
    try:
        questions = gemini_service.generate_questions(
            category=category,
            count=count,
            difficulty=difficulty,
            language=language
        )
        
        if not questions:
            return Response(
                {'error': 'Failed to generate questions'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Format questions for frontend
        formatted_questions = []
        for q in questions:
            formatted_questions.append({
                'id': None,  # AI-generated, no DB id
                'text': q['text'],
                'options': {
                    'A': q['option_a'],
                    'B': q['option_b'],
                    'C': q['option_c'],
                    'D': q['option_d'],
                },
                'correct_option': q['correct_option'],
                'explanation': q.get('explanation', ''),
                'category': category,
                'is_ai_generated': True,
            })
        
        return Response({'questions': formatted_questions})
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============ Offline Game ============

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def start_offline_game(request):
    """Start an offline game against AI bot"""
    user = request.user
    category = request.data.get('category', 'general')
    difficulty = request.data.get('difficulty', 'medium')
    use_ai_questions = request.data.get('use_ai_questions', True)
    
    # Get or generate questions
    questions_data = []
    
    if use_ai_questions:
        try:
            ai_questions = gemini_service.generate_questions(
                category=category,
                count=5,
                difficulty=difficulty,
                language='ru'
            )
            if ai_questions:
                questions_data = ai_questions
        except Exception as e:
            print(f"AI question generation failed: {e}")
    
    # Fallback to database questions
    if not questions_data:
        db_questions = list(Question.objects.order_by('?')[:5])
        for q in db_questions:
            questions_data.append({
                'text': q.text,
                'option_a': q.option_a,
                'option_b': q.option_b,
                'option_c': q.option_c,
                'option_d': q.option_d,
                'correct_option': q.correct_option,
                'explanation': q.explanation,
            })
    
    if not questions_data:
        return Response(
            {'error': 'No questions available'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Format questions for response
    formatted_questions = []
    for i, q in enumerate(questions_data):
        formatted_questions.append({
            'round': i + 1,
            'text': q['text'],
            'options': {
                'A': q['option_a'],
                'B': q['option_b'],
                'C': q['option_c'],
                'D': q['option_d'],
            },
            'correct_option': q['correct_option'],
            'explanation': q.get('explanation', ''),
        })
    
    # Create AI bot data
    bot_names = ['QuizBot', 'BrainMaster', 'SmartAI', 'QuizGenius', 'MindBot']
    bot = {
        'id': 0,
        'username': random.choice(bot_names),
        'rating': max(800, user.rating + random.randint(-200, 200)),
        'avatar': None,
        'is_bot': True,
    }
    
    return Response({
        'game_id': f"offline_{user.id}_{timezone.now().timestamp()}",
        'player': UserSerializer(user).data,
        'opponent': bot,
        'questions': formatted_questions,
        'total_rounds': len(formatted_questions),
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def finish_offline_game(request):
    """Save offline game results and update rating"""
    user = request.user
    my_score = int(request.data.get('my_score', 0))
    bot_score = int(request.data.get('bot_score', 0))
    
    # Determine winner
    is_winner = my_score > bot_score
    is_draw = my_score == bot_score
    
    # Update rating
    if not is_draw:
        if is_winner:
            user.rating += 15  # Less points for beating AI
            user.wins += 1
        else:
            user.rating = max(0, user.rating - 10)
            user.losses += 1
        
        user.level = (user.rating // 200) + 1
        user.save()
    
    return Response({
        'is_winner': is_winner,
        'is_draw': is_draw,
        'rating_change': 15 if is_winner else (-10 if not is_draw else 0),
        'new_rating': user.rating,
        'new_level': user.level,
    })


# ============ Google OAuth ============

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def google_auth(request):
    """
    Authenticate user with Google.
    Expects: { "id_token": "..." } - ID token from Google Sign-In
    """
    token = request.data.get('id_token')
    
    if not token:
        return Response(
            {'error': 'ID token is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Verify the token with Google
        # Accept tokens from both web and mobile clients
        client_ids = [
            settings.GOOGLE_CLIENT_ID,
            settings.GOOGLE_WEB_CLIENT_ID,
        ]
        
        idinfo = None
        for client_id in client_ids:
            try:
                idinfo = id_token.verify_oauth2_token(
                    token, 
                    google_requests.Request(), 
                    client_id
                )
                break
            except ValueError:
                continue
        
        if not idinfo:
            return Response(
                {'error': 'Invalid token'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Get user info from token
        google_id = idinfo['sub']
        email = idinfo.get('email', '')
        name = idinfo.get('name', '')
        picture = idinfo.get('picture', '')
        
        # Check if user exists with this Google ID
        try:
            user = User.objects.get(google_id=google_id)
            # Update user info if needed
            if picture and user.avatar != picture:
                user.avatar = picture
                user.save()
        except User.DoesNotExist:
            # Check if user exists with this email
            try:
                user = User.objects.get(email=email)
                # Link Google account to existing user
                user.google_id = google_id
                if picture:
                    user.avatar = picture
                user.save()
            except User.DoesNotExist:
                # Create new user
                import uuid
                username = name.replace(' ', '_') if name else f"user_{uuid.uuid4().hex[:8]}"
                
                # Make sure username is unique
                base_username = username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}_{counter}"
                    counter += 1
                
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=uuid.uuid4().hex,  # Random password
                    google_id=google_id,
                    avatar=picture,
                )
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'is_new_user': user.total_matches == 0,
        }, status=status.HTTP_200_OK)
        
    except ValueError as e:
        return Response(
            {'error': f'Invalid token: {str(e)}'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    except Exception as e:
        return Response(
            {'error': f'Authentication failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
