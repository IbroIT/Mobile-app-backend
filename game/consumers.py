import json
import asyncio
from datetime import datetime
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from api.models import User, Match, Round, Question, MatchHistory, Category


class MatchmakingConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for matchmaking"""
    
    # Class-level queue for waiting players
    waiting_players = {}
    
    async def connect(self):
        self.user = self.scope['user']
        
        if self.user.is_anonymous:
            await self.close()
            return
        
        await self.accept()
        await self.set_user_online(True)
        
        # Check if there's already someone waiting
        if MatchmakingConsumer.waiting_players:
            # Get the first waiting player
            opponent_id, opponent_channel = list(MatchmakingConsumer.waiting_players.items())[0]
            
            if opponent_id != self.user.id:
                # Remove opponent from waiting list
                del MatchmakingConsumer.waiting_players[opponent_id]
                
                # Create match
                match = await self.create_match(opponent_id)
                
                # Notify both players
                match_data = await self.get_match_data(match.id)
                
                # Send to opponent
                await self.channel_layer.send(
                    opponent_channel,
                    {
                        'type': 'match_found',
                        'match': match_data
                    }
                )
                
                # Send to current user
                await self.send(text_data=json.dumps({
                    'type': 'match_found',
                    'match': match_data
                }))
                return
        
        # No opponent found, add to waiting list
        MatchmakingConsumer.waiting_players[self.user.id] = self.channel_name
        
        await self.send(text_data=json.dumps({
            'type': 'matchmaking_start',
            'message': 'Looking for opponent...'
        }))
    
    async def disconnect(self, close_code):
        if hasattr(self, 'user') and not self.user.is_anonymous:
            # Remove from waiting list
            if self.user.id in MatchmakingConsumer.waiting_players:
                del MatchmakingConsumer.waiting_players[self.user.id]
            
            await self.set_user_online(False)
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')
        
        if action == 'cancel':
            if self.user.id in MatchmakingConsumer.waiting_players:
                del MatchmakingConsumer.waiting_players[self.user.id]
            
            await self.send(text_data=json.dumps({
                'type': 'matchmaking_cancelled'
            }))
    
    async def match_found(self, event):
        """Handler for match_found message type"""
        await self.send(text_data=json.dumps({
            'type': 'match_found',
            'match': event['match']
        }))
    
    @database_sync_to_async
    def set_user_online(self, is_online):
        User.objects.filter(id=self.user.id).update(is_online=is_online)
    
    @database_sync_to_async
    def create_match(self, opponent_id):
        opponent = User.objects.get(id=opponent_id)
        
        # Create match
        match = Match.objects.create(
            player1=opponent,  # First player to wait
            player2=self.user,  # Current player
            status='in_progress',
            started_at=timezone.now()
        )
        
        # Get random questions
        questions = list(Question.objects.order_by('?')[:5])
        
        # Create rounds
        for i, question in enumerate(questions, 1):
            Round.objects.create(
                match=match,
                round_number=i,
                question=question
            )
        
        # Update users
        User.objects.filter(id__in=[self.user.id, opponent_id]).update(is_in_game=True)
        
        return match
    
    @database_sync_to_async
    def get_match_data(self, match_id):
        match = Match.objects.select_related('player1', 'player2').get(id=match_id)
        return {
            'id': match.id,
            'player1': {
                'id': match.player1.id,
                'username': match.player1.username,
                'avatar': match.player1.avatar.url if match.player1.avatar else None,
                'rating': match.player1.rating,
            },
            'player2': {
                'id': match.player2.id,
                'username': match.player2.username,
                'avatar': match.player2.avatar.url if match.player2.avatar else None,
                'rating': match.player2.rating,
            },
            'total_rounds': match.total_rounds,
        }


class GameConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for game play"""
    
    # Store game state per match
    game_states = {}
    
    async def connect(self):
        self.user = self.scope['user']
        self.match_id = self.scope['url_route']['kwargs']['match_id']
        self.room_group_name = f'game_{self.match_id}'
        
        if self.user.is_anonymous:
            await self.close()
            return
        
        # Verify user is part of this match
        if not await self.verify_player():
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Initialize game state if needed
        if self.match_id not in GameConsumer.game_states:
            GameConsumer.game_states[self.match_id] = {
                'players_ready': set(),
                'current_round': 0,
                'round_answers': {},
                'round_start_time': None,
                'emojis_sent': {},
            }
        
        # Mark player as ready
        state = GameConsumer.game_states[self.match_id]
        state['players_ready'].add(self.user.id)
        
        # Send current game state
        await self.send(text_data=json.dumps({
            'type': 'connected',
            'match_id': int(self.match_id),
            'players_ready': len(state['players_ready'])
        }))
        
        # If both players are ready, start the game
        if len(state['players_ready']) >= 2:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'game_start',
                }
            )
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        # Clean up game state if empty
        if self.match_id in GameConsumer.game_states:
            state = GameConsumer.game_states[self.match_id]
            state['players_ready'].discard(self.user.id)
            if not state['players_ready']:
                del GameConsumer.game_states[self.match_id]
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')
        
        if action == 'ready':
            await self.handle_ready()
        elif action == 'answer':
            await self.handle_answer(data)
        elif action == 'emoji':
            await self.handle_emoji(data)
    
    async def handle_ready(self):
        """Handle player ready signal"""
        state = GameConsumer.game_states.get(self.match_id, {})
        
        if len(state.get('players_ready', set())) >= 2:
            # Start first round
            await self.start_round()
    
    async def handle_answer(self, data):
        """Handle player answer submission"""
        answer = data.get('answer')
        time_taken = data.get('time', 15)  # Default to max time
        
        state = GameConsumer.game_states.get(self.match_id)
        if not state:
            return
        
        current_round = state['current_round']
        
        # Initialize round answers if needed
        if current_round not in state['round_answers']:
            state['round_answers'][current_round] = {}
        
        # Don't allow duplicate answers
        if self.user.id in state['round_answers'][current_round]:
            return
        
        # Store answer
        state['round_answers'][current_round][self.user.id] = {
            'answer': answer,
            'time': time_taken
        }
        
        # Notify all players that someone answered
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'answer_submitted',
                'user_id': self.user.id,
            }
        )
        
        # Check if both players answered
        if len(state['round_answers'][current_round]) >= 2:
            await self.end_round()
    
    async def handle_emoji(self, data):
        """Handle emoji sending"""
        emoji = data.get('emoji')
        
        state = GameConsumer.game_states.get(self.match_id)
        if not state:
            return
        
        # Check emoji limit (5 per match)
        if self.user.id not in state['emojis_sent']:
            state['emojis_sent'][self.user.id] = 0
        
        if state['emojis_sent'][self.user.id] >= 5:
            return
        
        state['emojis_sent'][self.user.id] += 1
        
        # Broadcast emoji to opponent
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'emoji_received',
                'user_id': self.user.id,
                'emoji': emoji,
            }
        )
    
    async def start_round(self):
        """Start a new round"""
        state = GameConsumer.game_states.get(self.match_id)
        if not state:
            return
        
        state['current_round'] += 1
        state['round_start_time'] = timezone.now()
        
        # Get question for this round
        question_data = await self.get_round_question(state['current_round'])
        
        if question_data:
            # Update match current round
            await self.update_match_round(state['current_round'])
            
            # Broadcast question to all players
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'question_start',
                    'round': state['current_round'],
                    'question': question_data,
                }
            )
            
            # Start timeout timer
            asyncio.create_task(self.round_timeout(state['current_round']))
    
    async def round_timeout(self, round_number):
        """Handle round timeout after 15 seconds"""
        await asyncio.sleep(15)
        
        state = GameConsumer.game_states.get(self.match_id)
        if not state or state['current_round'] != round_number:
            return
        
        # Force end round if not all players answered
        if round_number in state['round_answers']:
            if len(state['round_answers'][round_number]) < 2:
                await self.end_round()
    
    async def end_round(self):
        """End current round and calculate scores"""
        state = GameConsumer.game_states.get(self.match_id)
        if not state:
            return
        
        current_round = state['current_round']
        answers = state['round_answers'].get(current_round, {})
        
        # Calculate scores and save to database
        round_result = await self.calculate_round_result(current_round, answers)
        
        # Broadcast round result
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'round_end',
                'round': current_round,
                'result': round_result,
            }
        )
        
        # Check if match is over
        match_data = await self.get_match_scores()
        
        if current_round >= match_data['total_rounds']:
            # End match
            await asyncio.sleep(2)  # Brief pause before showing final result
            await self.end_match()
        else:
            # Start next round after delay
            await asyncio.sleep(3)
            await self.start_round()
    
    async def end_match(self):
        """End the match and determine winner"""
        match_result = await self.finalize_match()
        
        # Broadcast match end
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'match_end',
                'result': match_result,
            }
        )
        
        # Clean up game state
        if self.match_id in GameConsumer.game_states:
            del GameConsumer.game_states[self.match_id]
    
    # WebSocket event handlers
    async def game_start(self, event):
        await self.send(text_data=json.dumps({
            'type': 'game_start',
            'message': 'Both players connected. Game starting...'
        }))
        
        # Start first round after VS screen
        await asyncio.sleep(3)
        await self.start_round()
    
    async def question_start(self, event):
        await self.send(text_data=json.dumps({
            'type': 'question_start',
            'round': event['round'],
            'question': event['question'],
        }))
    
    async def answer_submitted(self, event):
        await self.send(text_data=json.dumps({
            'type': 'answer_submitted',
            'user_id': event['user_id'],
        }))
    
    async def round_end(self, event):
        await self.send(text_data=json.dumps({
            'type': 'round_end',
            'round': event['round'],
            'result': event['result'],
        }))
    
    async def match_end(self, event):
        await self.send(text_data=json.dumps({
            'type': 'match_end',
            'result': event['result'],
        }))
    
    async def emoji_received(self, event):
        # Don't send emoji back to sender
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'emoji_received',
                'emoji': event['emoji'],
            }))
    
    # Database operations
    @database_sync_to_async
    def verify_player(self):
        return Match.objects.filter(
            id=self.match_id
        ).filter(
            models.Q(player1_id=self.user.id) | models.Q(player2_id=self.user.id)
        ).exists()
    
    @database_sync_to_async
    def get_round_question(self, round_number):
        try:
            round_obj = Round.objects.select_related('question', 'question__category').get(
                match_id=self.match_id,
                round_number=round_number
            )
            question = round_obj.question
            return {
                'id': question.id,
                'text': question.text,
                'options': {
                    'A': question.option_a,
                    'B': question.option_b,
                    'C': question.option_c,
                    'D': question.option_d,
                },
                'category': question.category.name,
            }
        except Round.DoesNotExist:
            return None
    
    @database_sync_to_async
    def update_match_round(self, round_number):
        Match.objects.filter(id=self.match_id).update(current_round=round_number)
    
    @database_sync_to_async
    def calculate_round_result(self, round_number, answers):
        round_obj = Round.objects.select_related('question', 'match').get(
            match_id=self.match_id,
            round_number=round_number
        )
        match = round_obj.match
        correct_answer = round_obj.question.correct_option
        
        result = {
            'correct_answer': correct_answer,
            'explanation': round_obj.question.explanation,
            'players': {}
        }
        
        # Process player 1
        p1_data = answers.get(match.player1_id, {})
        p1_answer = p1_data.get('answer')
        p1_time = p1_data.get('time', 15)
        p1_correct = p1_answer == correct_answer
        p1_score = round_obj.calculate_score(p1_time, p1_correct)
        
        round_obj.player1_answer = p1_answer
        round_obj.player1_time = p1_time
        round_obj.player1_score = p1_score
        
        result['players'][match.player1_id] = {
            'answer': p1_answer,
            'time': p1_time,
            'score': p1_score,
            'correct': p1_correct,
        }
        
        # Process player 2
        p2_data = answers.get(match.player2_id, {})
        p2_answer = p2_data.get('answer')
        p2_time = p2_data.get('time', 15)
        p2_correct = p2_answer == correct_answer
        p2_score = round_obj.calculate_score(p2_time, p2_correct)
        
        round_obj.player2_answer = p2_answer
        round_obj.player2_time = p2_time
        round_obj.player2_score = p2_score
        
        round_obj.save()
        
        result['players'][match.player2_id] = {
            'answer': p2_answer,
            'time': p2_time,
            'score': p2_score,
            'correct': p2_correct,
        }
        
        # Update match scores
        match.score1 += p1_score
        match.score2 += p2_score
        match.save()
        
        result['total_scores'] = {
            match.player1_id: match.score1,
            match.player2_id: match.score2,
        }
        
        return result
    
    @database_sync_to_async
    def get_match_scores(self):
        match = Match.objects.get(id=self.match_id)
        return {
            'score1': match.score1,
            'score2': match.score2,
            'total_rounds': match.total_rounds,
        }
    
    @database_sync_to_async
    def finalize_match(self):
        match = Match.objects.select_related('player1', 'player2').get(id=self.match_id)
        
        # Determine winner
        if match.score1 > match.score2:
            match.winner = match.player1
            p1_won = True
        elif match.score2 > match.score1:
            match.winner = match.player2
            p1_won = False
        else:
            match.winner = None  # Draw
            p1_won = None
        
        match.status = 'completed'
        match.ended_at = timezone.now()
        match.save()
        
        # Update player ratings
        if p1_won is not None:
            match.player1.update_rating(p1_won)
            match.player2.update_rating(not p1_won)
        
        # Update is_in_game status
        User.objects.filter(id__in=[match.player1_id, match.player2_id]).update(is_in_game=False)
        
        # Create match history entries
        MatchHistory.objects.create(
            user=match.player1,
            match=match,
            opponent=match.player2,
            user_score=match.score1,
            opponent_score=match.score2,
            is_winner=p1_won if p1_won is not None else False,
            rating_change=20 if p1_won else -15 if p1_won is False else 0
        )
        
        MatchHistory.objects.create(
            user=match.player2,
            match=match,
            opponent=match.player1,
            user_score=match.score2,
            opponent_score=match.score1,
            is_winner=not p1_won if p1_won is not None else False,
            rating_change=-15 if p1_won else 20 if p1_won is False else 0
        )
        
        # Get rounds for review
        rounds = []
        for round_obj in match.rounds.all().select_related('question'):
            rounds.append({
                'round_number': round_obj.round_number,
                'question': {
                    'text': round_obj.question.text,
                    'correct_answer': round_obj.question.correct_option,
                    'explanation': round_obj.question.explanation,
                },
                'player1_answer': round_obj.player1_answer,
                'player2_answer': round_obj.player2_answer,
                'player1_score': round_obj.player1_score,
                'player2_score': round_obj.player2_score,
            })
        
        return {
            'winner_id': match.winner.id if match.winner else None,
            'player1': {
                'id': match.player1.id,
                'username': match.player1.username,
                'score': match.score1,
                'new_rating': match.player1.rating,
            },
            'player2': {
                'id': match.player2.id,
                'username': match.player2.username,
                'score': match.score2,
                'new_rating': match.player2.rating,
            },
            'rounds': rounds,
        }


# Need to import models for Q lookup
from django.db import models
