# No Rats — API REST Implementation Guide

## 0. Estrutura de Apps Django — Justificativa

```
no_rats_backend/
├── manage.py
├── requirements.txt
├── no_rats/                  # Project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── accounts/                 # Auth + User profile
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── permissions.py
│   ├── urls.py
│   └── tests/
├── houses/                   # Rooms + Infestation
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── permissions.py
│   ├── urls.py
│   └── tests/
├── tasks/                    # Tasks + Completion + Expiry
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── permissions.py
│   ├── urls.py
│   ├── management/commands/
│   │   └── mark_expired_tasks.py
│   └── tests/
├── gamification/             # XP, Streak, Infestation logic
│   ├── services.py
│   ├── signals.py
│   └── tests/
└── core/                     # Shared (permissions, pagination, etc)
    ├── permissions.py
    ├── pagination.py
    └── exceptions.py
```

### Por que essa divisão?

| App | Responsabilidade | Justificativa |
|-----|------------------|---------------|
| **accounts** | User, auth JWT, profile | Isolado; fácil reusar em outros projetos Django |
| **houses** | Room + RoomInfestationEvent | Domínio "casa"; separado de tarefas |
| **tasks** | Task, TaskCompletion, CRUD | Domínio "tarefas"; gerenciamento completo do ciclo |
| **gamification** | XP, streak, infestação logic | Serviços puros (services) + signals; testável, reutilizável |
| **core** | Shared permissions, pagination, exceptions | DRY; usado por múltiplos apps |

---

## 1. Accounts App — Autenticação JWT & User

### 1.1 `accounts/models.py`

```python
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
from datetime import datetime

class UserManager(BaseUserManager):
    def create_user(self, email, password, name, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, name=name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, name, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, name, **extra_fields)

class User(AbstractBaseUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    name = models.CharField(max_length=150)
    avatar_url = models.URLField(blank=True, null=True)
    
    # XP & Level
    total_xp = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    level = models.IntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(12)])
    level_xp = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    
    # Streak
    streak = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    streak_safe_today = models.BooleanField(default=True)
    last_streak_check = models.DateTimeField(auto_now_add=True)
    
    # Infestação
    total_infestation = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # Admin
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']
    
    class Meta:
        db_table = 'users'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} (Nível {self.level})"
    
    def get_xp_for_next_level(self):
        xp_table = {
            1: 100, 2: 200, 3: 300, 4: 400, 5: 500,
            6: 600, 7: 700, 8: 800, 9: 900, 10: 1000,
            11: 1200, 12: 0,
        }
        return xp_table.get(self.level, 0)
    
    def recalculate_total_infestation(self):
        """CACHE: Recalcula média de rooms"""
        rooms = self.room_set.all()
        if not rooms.exists():
            avg = 0.0
        else:
            avg = rooms.aggregate(avg=models.Avg('infestation'))['avg'] or 0.0
        self.total_infestation = round(avg, 2)
        self.save(update_fields=['total_infestation', 'updated_at'])
```

### 1.2 `accounts/serializers.py`

```python
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User

class UserSerializer(serializers.ModelSerializer):
    xp_for_next_level = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'name', 'avatar_url',
            'total_xp', 'level', 'level_xp', 'streak',
            'total_infestation', 'xp_for_next_level',
            'created_at'
        ]
        read_only_fields = ['id', 'total_xp', 'level', 'level_xp', 'streak', 'total_infestation', 'created_at']
    
    def get_xp_for_next_level(self, obj):
        return obj.get_xp_for_next_level()

class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['email', 'name', 'password', 'password_confirm']
    
    def validate(self, data):
        if data['password'] != data.pop('password_confirm'):
            raise serializers.ValidationError({'password': 'Passwords do not match'})
        return data
    
    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            name=validated_data['name'],
            password=validated_data['password']
        )
        return user

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """JWT token com dados de usuário"""
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email
        token['name'] = user.name
        return token
```

### 1.3 `accounts/views.py`

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .models import User
from .serializers import UserSerializer, UserRegisterSerializer, CustomTokenObtainPairSerializer
from core.permissions import IsOwnerOnly

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsOwnerOnly]
    
    def get_queryset(self):
        return User.objects.filter(id=self.request.user.id)
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def register(self, request):
        """POST /api/users/register/"""
        serializer = UserRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                UserSerializer(user).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """GET /api/users/me/ — Dados do usuário autenticado"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put'], permission_classes=[IsAuthenticated])
    def update_profile(self, request):
        """PUT /api/users/update_profile/ — Atualizar perfil"""
        user = request.user
        serializer = self.get_serializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```

### 1.4 `accounts/permissions.py`

```python
# Para usar em qualquer view que queira IsOwnerOnly
# Vide core/permissions.py
```

### 1.5 `accounts/urls.py`

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import UserViewSet, CustomTokenObtainPairView

router = DefaultRouter()
router.register('users', UserViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)),
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
```

---

## 2. Houses App — Rooms & Infestation

### 2.1 `houses/models.py`

```python
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid

class Room(models.Model):
    ROOM_CHOICES = (
        ('cozinha', 'Cozinha'),
        ('banheiro', 'Banheiro'),
        ('quarto', 'Quarto'),
        ('sala', 'Sala'),
        ('lavanderia', 'Lavanderia'),
        ('escritorio', 'Escritório'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    name = models.CharField(max_length=50, choices=ROOM_CHOICES)
    infestation = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'rooms'
        unique_together = ('user', 'name')
        ordering = ['name']
    
    def __str__(self):
        return f"{self.user.name} - {self.get_name_display()} ({self.infestation}%)"
    
    def add_infestation(self, delta):
        """Aumenta/diminui infestação (0-100)"""
        new_inf = max(0, min(100, self.infestation + delta))
        self.infestation = round(new_inf, 2)
        self.save(update_fields=['infestation', 'updated_at'])
        self.user.recalculate_total_infestation()

class RoomInfestationEvent(models.Model):
    REASON_CHOICES = (
        ('task_completed', 'Tarefa Completada'),
        ('task_expired', 'Tarefa Vencida'),
        ('manual_adjustment', 'Ajuste Manual'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    task = models.ForeignKey('tasks.Task', on_delete=models.CASCADE, null=True, blank=True)
    
    delta = models.FloatField()
    reason = models.CharField(max_length=30, choices=REASON_CHOICES)
    
    difficulty_multiplier = models.FloatField(null=True, blank=True)
    frequency_multiplier = models.FloatField(null=True, blank=True)
    time_overdue_multiplier = models.FloatField(null=True, blank=True)
    
    infestation_after = models.FloatField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'room_infestation_events'
        ordering = ['-created_at']

# Signal para recalcular total_infestation quando Room muda
@receiver(post_save, sender=Room)
def room_infestation_changed(sender, instance, created, **kwargs):
    if not created:
        instance.user.recalculate_total_infestation()
```

### 2.2 `houses/serializers.py`

```python
from rest_framework import serializers
from .models import Room, RoomInfestationEvent

class RoomSerializer(serializers.ModelSerializer):
    room_name = serializers.CharField(source='get_name_display', read_only=True)
    
    class Meta:
        model = Room
        fields = ['id', 'name', 'room_name', 'infestation', 'created_at']
        read_only_fields = ['id', 'infestation', 'created_at']

class RoomInfestationEventSerializer(serializers.ModelSerializer):
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    
    class Meta:
        model = RoomInfestationEvent
        fields = [
            'id', 'room', 'delta', 'reason', 'reason_display',
            'difficulty_multiplier', 'frequency_multiplier',
            'time_overdue_multiplier', 'infestation_after', 'created_at'
        ]
        read_only_fields = '__all__'
```

### 2.3 `houses/views.py`

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Room, RoomInfestationEvent
from .serializers import RoomSerializer, RoomInfestationEventSerializer
from core.permissions import IsOwnerOnly

class RoomViewSet(viewsets.ModelViewSet):
    serializer_class = RoomSerializer
    permission_classes = [IsAuthenticated, IsOwnerOnly]
    
    def get_queryset(self):
        return Room.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def setup_house(self, request):
        """
        POST /api/rooms/setup_house/
        {
            "rooms": ["cozinha", "banheiro", "quarto"]
        }
        Cria todos os cômodos selecionados para o usuário (onboarding)
        """
        room_names = request.data.get('rooms', [])
        if not room_names:
            return Response(
                {'error': 'rooms list required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = request.user
        created_rooms = []
        
        for room_name in room_names:
            room, created = Room.objects.get_or_create(
                user=user,
                name=room_name
            )
            if created:
                created_rooms.append(room)
        
        serializer = self.get_serializer(created_rooms, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class RoomInfestationEventViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RoomInfestationEventSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return RoomInfestationEvent.objects.filter(user=self.request.user)
```

### 2.4 `houses/urls.py`

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RoomViewSet, RoomInfestationEventViewSet

router = DefaultRouter()
router.register('rooms', RoomViewSet, basename='room')
router.register('room-events', RoomInfestationEventViewSet, basename='room-event')

urlpatterns = [
    path('', include(router.urls)),
]
```

---

## 3. Tasks App — CRUD & Completion

### 3.1 `tasks/models.py`

```python
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import datetime, timedelta
import uuid

class Task(models.Model):
    DIFFICULTY_CHOICES = (
        ('simples', 'Simples'),
        ('media', 'Média'),
        ('dificil', 'Difícil'),
        ('pesada', 'Pesada'),
    )
    
    DIFFICULTY_MAP = {
        'simples': 10,
        'media': 25,
        'dificil': 50,
        'pesada': 100,
    }
    
    FREQUENCY_CHOICES = (
        ('diaria', 'Diária'),
        ('semanal', 'Semanal'),
        ('quinzenal', 'Quinzenal'),
        ('mensal', 'Mensal'),
    )
    
    FREQUENCY_DAYS = {
        'diaria': 1,
        'semanal': 7,
        'quinzenal': 14,
        'mensal': 30,
    }
    
    STATUS_CHOICES = (
        ('pendente', 'Pendente'),
        ('concluida', 'Concluída'),
        ('vencida', 'Vencida'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    room = models.ForeignKey('houses.Room', on_delete=models.CASCADE)
    
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True, max_length=500)
    category = models.CharField(max_length=50, blank=True, null=True)
    
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    
    due_date = models.DateTimeField(db_index=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pendente',
        db_index=True
    )
    
    xp_value = models.IntegerField(validators=[MinValueValidator(10)])
    
    recurring = models.BooleanField(default=True)
    parent_task = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recurrences'
    )
    
    completed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tasks'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'room', 'status']),
            models.Index(fields=['due_date', 'status']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} ({self.room.get_name_display()}) - {self.status}"
    
    def is_overdue(self):
        if self.status in ['concluida', 'vencida']:
            return False
        return datetime.now() > self.due_date
    
    def calculate_infestation_delta(self):
        """Fórmula SPEC.md: dificuldade × frequência × tempo_vencido"""
        difficulty_map = {
            'simples': 2,
            'media': 4,
            'dificil': 8,
            'pesada': 15,
        }
        
        frequency_map = {
            'diaria': 1.5,
            'semanal': 1.0,
            'quinzenal': 0.8,
            'mensal': 0.5,
        }
        
        now = datetime.now()
        if now <= self.due_date:
            time_mult = 1.0
        else:
            hours_overdue = (now - self.due_date).total_seconds() / 3600
            if hours_overdue <= 24:
                time_mult = 1.0
            elif hours_overdue <= 72:
                time_mult = 1.3
            elif hours_overdue <= 168:
                time_mult = 1.6
            else:
                time_mult = 2.0
        
        delta = (
            difficulty_map[self.difficulty]
            * frequency_map[self.frequency]
            * time_mult
        )
        return min(15, delta)
    
    def mark_expired(self):
        if self.status == 'pendente':
            self.status = 'vencida'
            self.save(update_fields=['status', 'updated_at'])
    
    def get_next_due_date(self):
        """Calcula próximo prazo para tarefa recorrente"""
        days = self.FREQUENCY_DAYS[self.frequency]
        if self.completed_at:
            return self.completed_at + timedelta(days=days)
        return self.due_date + timedelta(days=days)

class TaskCompletion(models.Model):
    """Log de cada conclusão de tarefa"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='completions')
    room = models.ForeignKey('houses.Room', on_delete=models.CASCADE)
    
    completed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    xp_earned = models.IntegerField(validators=[MinValueValidator(10)])
    streak_maintained = models.BooleanField(default=True)
    infestation_cleared = models.FloatField(default=0.0, validators=[MinValueValidator(0)])
    
    level_before = models.IntegerField()
    level_after = models.IntegerField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'task_completions'
        ordering = ['-completed_at']
    
    def __str__(self):
        return f"{self.user.name} completou {self.task.title}"
```

### 3.2 `tasks/serializers.py`

```python
from rest_framework import serializers
from .models import Task, TaskCompletion

class TaskSerializer(serializers.ModelSerializer):
    room_name = serializers.CharField(source='room.get_name_display', read_only=True)
    difficulty_display = serializers.CharField(source='get_difficulty_display', read_only=True)
    frequency_display = serializers.CharField(source='get_frequency_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_overdue = serializers.SerializerMethodField()
    xp_value = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Task
        fields = [
            'id', 'room', 'room_name', 'title', 'description', 'category',
            'difficulty', 'difficulty_display', 'frequency', 'frequency_display',
            'due_date', 'status', 'status_display', 'xp_value',
            'recurring', 'completed_at', 'is_overdue', 'created_at'
        ]
        read_only_fields = ['id', 'xp_value', 'completed_at', 'created_at']
    
    def validate_room(self, value):
        if value.user != self.context['request'].user:
            raise serializers.ValidationError('Room does not belong to you')
        return value
    
    def create(self, validated_data):
        task = Task.objects.create(**validated_data)
        # Set xp_value baseado em difficulty
        task.xp_value = Task.DIFFICULTY_MAP[task.difficulty]
        task.save(update_fields=['xp_value'])
        return task
    
    def get_is_overdue(self, obj):
        return obj.is_overdue()

class TaskCompletionSerializer(serializers.ModelSerializer):
    task_title = serializers.CharField(source='task.title', read_only=True)
    room_name = serializers.CharField(source='room.get_name_display', read_only=True)
    
    class Meta:
        model = TaskCompletion
        fields = [
            'id', 'task', 'task_title', 'room', 'room_name',
            'xp_earned', 'streak_maintained', 'infestation_cleared',
            'level_before', 'level_after', 'completed_at'
        ]
        read_only_fields = '__all__'

class TaskCompleteSerializer(serializers.Serializer):
    """Input serializer para POST /tasks/:id/complete/"""
    pass  # Sem fields; lógica toda em view
```

### 3.3 `tasks/views.py`

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import Task, TaskCompletion
from .serializers import TaskSerializer, TaskCompletionSerializer, TaskCompleteSerializer
from core.permissions import IsOwnerOnly
from gamification.services import complete_task_service

class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated, IsOwnerOnly]
    
    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """
        POST /api/tasks/:id/complete/
        Marca tarefa como concluída e executa lógica de gamificação
        """
        task = self.get_object()
        
        if task.status == 'concluida':
            return Response(
                {'error': 'Task already completed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            completion, user_updated = complete_task_service(task)
            return Response({
                'completion': TaskCompletionSerializer(completion).data,
                'user': {
                    'total_xp': user_updated.total_xp,
                    'level': user_updated.level,
                    'level_xp': user_updated.level_xp,
                    'streak': user_updated.streak,
                    'total_infestation': user_updated.total_infestation,
                }
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """GET /api/tasks/pending/ — Tarefas pendentes"""
        tasks = self.get_queryset().filter(status='pendente').order_by('due_date')
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def completed(self, request):
        """GET /api/tasks/completed/ — Tarefas concluídas"""
        tasks = self.get_queryset().filter(status='concluida').order_by('-completed_at')
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)

class TaskCompletionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TaskCompletionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return TaskCompletion.objects.filter(user=self.request.user)
```

### 3.4 `tasks/urls.py`

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TaskViewSet, TaskCompletionViewSet

router = DefaultRouter()
router.register('tasks', TaskViewSet, basename='task')
router.register('task-completions', TaskCompletionViewSet, basename='task-completion')

urlpatterns = [
    path('', include(router.urls)),
]
```

### 3.5 `tasks/management/commands/mark_expired_tasks.py`

```python
from django.core.management.base import BaseCommand
from django.utils import timezone
from tasks.models import Task
from houses.models import RoomInfestationEvent
from accounts.models import User

class Command(BaseCommand):
    help = 'Mark tasks as expired and update infestation (run via cron or celery)'

    def handle(self, *args, **options):
        now = timezone.now()
        
        # Find all pending tasks that are overdue
        expired_tasks = Task.objects.filter(
            status='pendente',
            due_date__lt=now
        )
        
        for task in expired_tasks:
            # Calculate infestation delta
            delta = task.calculate_infestation_delta()
            
            # Update room infestation
            task.room.add_infestation(delta)
            
            # Log event
            RoomInfestationEvent.objects.create(
                user=task.user,
                room=task.room,
                task=task,
                delta=delta,
                reason='task_expired',
                difficulty_multiplier=task.DIFFICULTY_MAP[task.difficulty],
                frequency_multiplier={
                    'diaria': 1.5,
                    'semanal': 1.0,
                    'quinzenal': 0.8,
                    'mensal': 0.5,
                }[task.frequency],
                time_overdue_multiplier=self._calculate_time_multiplier(task),
                infestation_after=task.room.infestation
            )
            
            # Mark task as expired
            task.mark_expired()
            
            # Reset streak if it was safe today
            if task.user.streak_safe_today:
                task.user.streak = 0
                task.user.streak_safe_today = False
                task.user.save(update_fields=['streak', 'streak_safe_today', 'updated_at'])
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully marked {expired_tasks.count()} tasks as expired')
        )
    
    def _calculate_time_multiplier(self, task):
        from datetime import datetime
        now = datetime.now()
        if now <= task.due_date:
            return 1.0
        hours_overdue = (now - task.due_date).total_seconds() / 3600
        if hours_overdue <= 24:
            return 1.0
        elif hours_overdue <= 72:
            return 1.3
        elif hours_overdue <= 168:
            return 1.6
        else:
            return 2.0
```

---

## 4. Gamification App — Core Logic

### 4.1 `gamification/services.py`

```python
"""
Serviços de gamificação isolados de views.
Lógica pura, testável.
"""

from django.utils import timezone
from django.db.models import Q
from datetime import datetime, timedelta
from tasks.models import Task, TaskCompletion
from houses.models import RoomInfestationEvent
from accounts.models import User

def complete_task_service(task):
    """
    Marca tarefa como concluída, calcula XP, atualiza streak, infestação.
    
    Returns:
        (TaskCompletion, User) — completion record e user updated
    """
    if task.status == 'concluida':
        raise ValueError('Task already completed')
    
    user = task.user
    room = task.room
    
    # Capture estado anterior
    level_before = user.level
    
    # 1. Calcular XP
    xp_earned = task.xp_value
    user.total_xp += xp_earned
    
    # 2. Check nível up
    xp_for_next = user.get_xp_for_next_level()
    
    # Avançar níveis enquanto possível
    while user.total_xp >= xp_for_next and user.level < 12:
        user.total_xp -= xp_for_next
        user.level += 1
        xp_for_next = user.get_xp_for_next_level()
    
    # Atualizar level_xp (progressão visual na barra)
    user.level_xp = int((user.total_xp / xp_for_next * 100)) if xp_for_next > 0 else 0
    
    # 3. Atualizar streak
    # Streak incrementa se nenhuma tarefa venceu hoje
    today = timezone.now().date()
    any_expired_today = Task.objects.filter(
        user=user,
        status='vencida',
        updated_at__date=today
    ).exists()
    
    streak_maintained = not any_expired_today
    if streak_maintained:
        user.streak += 1
    else:
        user.streak = 0
    
    # 4. Atualizar infestação
    # Se tarefa estava vencida, remove a infestação que causou
    infestation_cleared = 0.0
    if task.status == 'vencida':
        # Buscar último event que aumentou a infestação
        last_event = RoomInfestationEvent.objects.filter(
            task=task,
            reason='task_expired'
        ).order_by('-created_at').first()
        
        if last_event:
            infestation_cleared = last_event.delta
            room.add_infestation(-infestation_cleared)
    
    # 5. Marcar como concluída
    task.status = 'concluida'
    task.completed_at = timezone.now()
    task.save(update_fields=['status', 'completed_at', 'updated_at'])
    
    # 6. Criar TaskCompletion record
    completion = TaskCompletion.objects.create(
        user=user,
        task=task,
        room=room,
        xp_earned=xp_earned,
        streak_maintained=streak_maintained,
        infestation_cleared=infestation_cleared,
        level_before=level_before,
        level_after=user.level,
    )
    
    # 7. Salvar usuário
    user.save(update_fields=[
        'total_xp', 'level', 'level_xp', 'streak', 'updated_at'
    ])
    
    # 8. Criar tarefa recorrente se necessário
    if task.recurring:
        next_due = task.get_next_due_date()
        Task.objects.create(
            user=user,
            room=room,
            title=task.title,
            description=task.description,
            category=task.category,
            difficulty=task.difficulty,
            frequency=task.frequency,
            due_date=next_due,
            xp_value=task.xp_value,
            recurring=task.recurring,
            parent_task=task,
        )
    
    return completion, user

def expire_task_service(task):
    """
    Marca tarefa como vencida e aumenta infestação.
    """
    if task.status != 'pendente':
        return
    
    user = task.user
    delta = task.calculate_infestation_delta()
    
    # Atualizar room infestation
    task.room.add_infestation(delta)
    
    # Log event
    RoomInfestationEvent.objects.create(
        user=user,
        room=task.room,
        task=task,
        delta=delta,
        reason='task_expired',
        difficulty_multiplier={
            'simples': 2,
            'media': 4,
            'dificil': 8,
            'pesada': 15,
        }[task.difficulty],
        frequency_multiplier={
            'diaria': 1.5,
            'semanal': 1.0,
            'quinzenal': 0.8,
            'mensal': 0.5,
        }[task.frequency],
        time_overdue_multiplier=_calculate_time_multiplier(task),
        infestation_after=task.room.infestation,
    )
    
    # Mark expired
    task.mark_expired()
    
    # Reset streak
    user.streak = 0
    user.streak_safe_today = False
    user.save(update_fields=['streak', 'streak_safe_today', 'updated_at'])

def _calculate_time_multiplier(task):
    now = timezone.now()
    if now <= task.due_date:
        return 1.0
    hours_overdue = (now - task.due_date).total_seconds() / 3600
    if hours_overdue <= 24:
        return 1.0
    elif hours_overdue <= 72:
        return 1.3
    elif hours_overdue <= 168:
        return 1.6
    else:
        return 2.0
```

### 4.2 `gamification/signals.py`

```python
"""
Django signals para atualizar caches automaticamente.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from houses.models import Room
from accounts.models import User

@receiver(post_save, sender=Room)
def room_infestation_changed(sender, instance, created, **kwargs):
    """Recalcula total_infestation quando Room muda"""
    if not created:
        instance.user.recalculate_total_infestation()

# Config em gamification/apps.py:
# class GamificationConfig(AppConfig):
#     name = 'gamification'
#     def ready(self):
#         import gamification.signals
```

---

## 5. Core App — Shared Utilities

### 5.1 `core/permissions.py`

```python
from rest_framework import permissions

class IsOwnerOnly(permissions.BasePermission):
    """
    Usuário só acessa seus próprios dados.
    """
    def has_object_permission(self, request, view, obj):
        # Para User, Room, Task, etc
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return obj == request.user

class IsAuthenticated(permissions.IsAuthenticated):
    """Alias do IsAuthenticated do DRF"""
    pass
```

### 5.2 `core/pagination.py`

```python
from rest_framework.pagination import PageNumberPagination

class DefaultPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 1000
```

### 5.3 `core/exceptions.py`

```python
from rest_framework.exceptions import APIException

class TaskAlreadyCompletedException(APIException):
    status_code = 400
    default_detail = 'Task is already completed.'

class InsufficientPermissionException(APIException):
    status_code = 403
    default_detail = 'You do not have permission to access this resource.'
```

---

## 6. Project Settings & URLs

### 6.1 `no_rats/settings.py` (Updates)

```python
import os
from pathlib import Path
from datetime import timedelta

# ... BASE_DIR, DEBUG, etc ...

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    
    # Local apps
    'accounts.apps.AccountsConfig',
    'houses.apps.HousesConfig',
    'tasks.apps.TasksConfig',
    'gamification.apps.GamificationConfig',
    'core.apps.CoreConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'no_rats'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'postgres'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# DRF Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'core.pagination.DefaultPagination',
    'DEFAULT_FILTER_BACKENDS': [
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
    },
}

# JWT Configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': os.getenv('DJANGO_SECRET_KEY', 'secret-key-dev'),
}

# CORS
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://localhost:5173',  # Vite default
    'https://yourdomain.com',
]

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
```

### 6.2 `no_rats/urls.py`

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('accounts.urls')),
    path('api/v1/houses/', include('houses.urls')),
    path('api/v1/tasks/', include('tasks.urls')),
]
```

### 6.3 `requirements.txt`

```txt
Django==4.2.0
djangorestframework==3.14.0
djangorestframework-simplejwt==5.2.0
django-cors-headers==4.0.0
psycopg2-binary==2.9.6
python-decouple==3.8
celery==5.3.0
redis==4.5.0
pytest==7.3.0
pytest-django==4.5.2
pytest-cov==4.0.0
factory-boy==3.2.1
```

---

## 7. Tests — Gamification Logic

### 7.1 `tasks/tests/test_gamification.py`

```python
import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
from tasks.models import Task, TaskCompletion
from houses.models import Room
from gamification.services import complete_task_service, expire_task_service

User = get_user_model()

@pytest.mark.django_db
class TestGameification:
    
    def setup_method(self):
        """Setup user, room, task"""
        self.user = User.objects.create_user(
            email='test@example.com',
            name='Test User',
            password='password'
        )
        self.room = Room.objects.create(user=self.user, name='cozinha')
        self.task = Task.objects.create(
            user=self.user,
            room=self.room,
            title='Lavar louça',
            difficulty='simples',
            frequency='diaria',
            due_date=timezone.now() + timedelta(hours=24),
            xp_value=10,
            recurring=False,
        )
    
    def test_complete_task_awards_xp(self):
        """Completar tarefa simples deve dar 10 XP"""
        initial_xp = self.user.total_xp
        completion, user = complete_task_service(self.task)
        
        assert completion.xp_earned == 10
        assert user.total_xp == initial_xp + 10
        assert self.task.status == 'concluida'
    
    def test_complete_task_maintains_streak(self):
        """Completar tarefa no prazo mantém streak"""
        self.user.streak = 5
        self.user.save()
        
        completion, user = complete_task_service(self.task)
        
        assert completion.streak_maintained == True
        assert user.streak == 6
    
    def test_level_progression(self):
        """Atingir XP para próximo nível sobe nível"""
        # User começa nível 1
        assert self.user.level == 1
        
        # Simular 100 XP (próximo nível)
        self.user.total_xp = 100
        self.user.save()
        
        # Completar tarefa de 50 XP (50+100=150)
        self.task.xp_value = 50
        self.task.save()
        
        completion, user = complete_task_service(self.task)
        
        # Deve estar nível 2 com 50 XP restantes
        assert user.level == 2
        assert user.total_xp == 50
    
    def test_expire_task_increases_infestation(self):
        """Tarefa vencida aumenta infestação do cômodo"""
        # Tarefa diária simples vence em 24h
        # Delta = 2 (dificuldade) * 1.5 (freq) * 1.0 (tempo) = 3
        self.task.due_date = timezone.now() - timedelta(hours=25)
        self.task.status = 'pendente'
        self.task.save()
        
        initial_inf = self.room.infestation
        expire_task_service(self.task)
        
        self.room.refresh_from_db()
        assert self.room.infestation > initial_inf
    
    def test_expire_task_resets_streak(self):
        """Tarefa vencida reseta streak"""
        self.user.streak = 10
        self.user.save()
        
        self.task.due_date = timezone.now() - timedelta(hours=25)
        self.task.status = 'pendente'
        self.task.save()
        
        expire_task_service(self.task)
        
        self.user.refresh_from_db()
        assert self.user.streak == 0
    
    def test_recurring_task_creates_next(self):
        """Completar tarefa recorrente cria próxima"""
        self.task.recurring = True
        self.task.save()
        
        initial_count = Task.objects.filter(room=self.room).count()
        
        completion, user = complete_task_service(self.task)
        
        # Deve haver uma nova tarefa
        assert Task.objects.filter(room=self.room).count() == initial_count + 1
        
        # Nova tarefa deve ter parent_task
        new_task = Task.objects.filter(parent_task=self.task).first()
        assert new_task is not None
        assert new_task.status == 'pendente'
    
    def test_infestation_cleared_when_completing_expired(self):
        """Completar tarefa vencida remove infestação causada"""
        # Expire task first
        self.task.due_date = timezone.now() - timedelta(hours=25)
        self.task.status = 'pendente'
        self.task.save()
        
        expire_task_service(self.task)
        
        infestation_after_expire = self.room.infestation
        
        # Now complete the expired task
        self.task.refresh_from_db()
        completion, user = complete_task_service(self.task)
        
        self.room.refresh_from_db()
        
        # Infestação deve voltar a 0
        assert self.room.infestation == 0.0
        assert completion.infestation_cleared > 0
    
    def test_total_infestation_is_average(self):
        """Total infestation = média de rooms"""
        room2 = Room.objects.create(user=self.user, name='banheiro')
        room3 = Room.objects.create(user=self.user, name='quarto')
        
        # Set infestations
        self.room.infestation = 30
        self.room.save()
        
        room2.infestation = 60
        room2.save()
        
        room3.infestation = 0
        room3.save()
        
        self.user.recalculate_total_infestation()
        
        # (30 + 60 + 0) / 3 = 30
        assert self.user.total_infestation == 30.0
```

### 7.2 `accounts/tests/test_auth.py`

```python
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()

@pytest.mark.django_db
class TestAuth:
    
    def setup_method(self):
        self.client = APIClient()
    
    def test_register_user(self):
        """POST /api/v1/auth/users/register/"""
        response = self.client.post('/api/v1/auth/users/register/', {
            'email': 'new@example.com',
            'name': 'New User',
            'password': 'password123',
            'password_confirm': 'password123',
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['email'] == 'new@example.com'
        assert User.objects.filter(email='new@example.com').exists()
    
    def test_login_returns_token(self):
        """POST /api/v1/auth/token/"""
        User.objects.create_user(
            email='test@example.com',
            name='Test',
            password='password123'
        )
        
        response = self.client.post('/api/v1/auth/token/', {
            'email': 'test@example.com',
            'password': 'password123',
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data
    
    def test_get_user_profile(self):
        """GET /api/v1/auth/users/me/"""
        user = User.objects.create_user(
            email='test@example.com',
            name='Test',
            password='password123'
        )
        
        self.client.force_authenticate(user=user)
        response = self.client.get('/api/v1/auth/users/me/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == 'test@example.com'
```

---

## 8. App Configs

### 8.1 `accounts/apps.py`

```python
from django.apps import AppConfig

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
```

### 8.2 `gamification/apps.py`

```python
from django.apps import AppConfig

class GamificationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gamification'
    
    def ready(self):
        import gamification.signals  # Carregar signals ao iniciar
```

---

## 9. Running Tests

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test
pytest tasks/tests/test_gamification.py::TestGameification::test_complete_task_awards_xp

# Run management command
python manage.py mark_expired_tasks

# Run on schedule with celery beat (futuro)
celery -A no_rats beat
```

---

## 10. Resumo da Arquitetura

| Componente | Responsabilidade |
|------------|------------------|
| **accounts** | User, auth JWT, profile |
| **houses** | Rooms, infestation events, eventos auditoria |
| **tasks** | Task CRUD, completion, recurrence |
| **gamification** | Services (XP, streak, infestação), signals |
| **core** | Permissions, pagination, exceptions |

**Fluxo de uma conclusão de tarefa:**
1. POST `/api/tasks/:id/complete/` → view chamada
2. View chama `complete_task_service(task)`
3. Service calcula XP, nível, streak, infestação
4. Cria `TaskCompletion` record (auditoria)
5. Se recorrente, cria nova tarefa
6. Retorna `(TaskCompletion, User)` atualizado
7. View serializa e retorna ao frontend

**Fluxo de vencimento automático:**
1. Management command ou Celery job roda `mark_expired_tasks`
2. Job busca todas as pending com due_date < now
3. Para cada, calcula infestação e chama `expire_task_service`
4. Service marca como vencida, aumenta infestação, reseta streak
5. Cria `RoomInfestationEvent` (auditoria)

---

**Status:** Pronto para scaffolding de projeto Django e testes.
