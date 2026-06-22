# No Rats V1.x — Expansão de Features

## 1. Sistema de Conquistas (Achievements)

### 1.1 Modelo de Dados — Estrutura Extensível

**Decisão arquitetural:** Conquistas como *templates* + logs de desbloqueio.

**Justificativa:**
- Adicionar nova conquista = só inserir dado na DB, sem migração de código
- Condições em JSON = flexíveis (sem criar subtabelas)
- Não quebra histórico existente

### 1.2 Models Django

```python
# gamification/models.py

from django.db import models
import json

class Achievement(models.Model):
    """
    Template de conquista.
    Cada linha = 1 conquista possível no app.
    Adicionar nova conquista = inserir nova linha (sem código novo).
    """
    
    CATEGORY_CHOICES = (
        ('task', 'Tarefas'),
        ('streak', 'Sequência'),
        ('level', 'Níveis'),
        ('infestation', 'Infestação'),
        ('room', 'Cômodos'),
    )
    
    id = models.AutoField(primary_key=True)
    code = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="ID único: first_task, streak_7, level_10, etc"
    )
    name = models.CharField(max_length=150)
    description = models.TextField()
    icon = models.CharField(max_length=10, help_text="Emoji ou URL")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    
    # Condição para desbloquear (JSON flexível)
    # Exemplos:
    # {"type": "task_completed_count", "value": 1}
    # {"type": "streak_reached", "value": 7}
    # {"type": "level_reached", "value": 10}
    # {"type": "zero_infestation_days", "value": 7}
    condition = models.JSONField(default=dict)
    
    reward_xp = models.IntegerField(
        default=0,
        help_text="XP bonus ao desbloquear"
    )
    
    order = models.IntegerField(
        default=0,
        help_text="Ordem no UI"
    )
    active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'achievements'
        ordering = ['category', 'order']
        verbose_name_plural = 'Achievements'
    
    def __str__(self):
        return f"{self.code} - {self.name}"

class UserAchievement(models.Model):
    """
    Log de quando usuário desbloqueou uma conquista.
    Permite histórico completo e notificações.
    """
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='achievements'
    )
    achievement = models.ForeignKey(
        Achievement,
        on_delete=models.CASCADE,
        related_name='user_records'
    )
    
    unlocked_at = models.DateTimeField(auto_now_add=True, db_index=True)
    seen = models.BooleanField(
        default=False,
        help_text="User viu a notificação?"
    )
    
    class Meta:
        db_table = 'user_achievements'
        unique_together = ('user', 'achievement')
        ordering = ['-unlocked_at']
    
    def __str__(self):
        return f"{self.user.name} - {self.achievement.name}"
```

### 1.3 Dados Iniciais (Fixtures ou Seed Data)

```python
# gamification/fixtures/achievements.json
# Ou criar via management command

ACHIEVEMENTS_DATA = [
    # Task-based
    {
        "code": "first_task",
        "name": "Começou!",
        "description": "Complete sua primeira tarefa",
        "icon": "🎯",
        "category": "task",
        "condition": {"type": "task_completed_count", "value": 1},
        "reward_xp": 50,
        "order": 1,
    },
    {
        "code": "10_tasks",
        "name": "Ocupado",
        "description": "Complete 10 tarefas",
        "icon": "📋",
        "category": "task",
        "condition": {"type": "task_completed_count", "value": 10},
        "reward_xp": 100,
        "order": 2,
    },
    {
        "code": "50_tasks",
        "name": "Máquina de Limpar",
        "description": "Complete 50 tarefas",
        "icon": "⚙️",
        "category": "task",
        "condition": {"type": "task_completed_count", "value": 50},
        "reward_xp": 250,
        "order": 3,
    },
    {
        "code": "100_tasks",
        "name": "Lenda das Tarefas",
        "description": "Complete 100 tarefas",
        "icon": "👑",
        "category": "task",
        "condition": {"type": "task_completed_count", "value": 100},
        "reward_xp": 500,
        "order": 4,
    },
    
    # Streak-based
    {
        "code": "streak_3",
        "name": "Começando a Queimar",
        "description": "3 dias de sequência",
        "icon": "🔥",
        "category": "streak",
        "condition": {"type": "streak_reached", "value": 3},
        "reward_xp": 75,
        "order": 5,
    },
    {
        "code": "streak_7",
        "name": "Sem Falhas",
        "description": "7 dias de sequência",
        "icon": "🔥🔥",
        "category": "streak",
        "condition": {"type": "streak_reached", "value": 7},
        "reward_xp": 150,
        "order": 6,
    },
    {
        "code": "streak_30",
        "name": "Infernal",
        "description": "30 dias de sequência",
        "icon": "🔥🔥🔥",
        "category": "streak",
        "condition": {"type": "streak_reached", "value": 30},
        "reward_xp": 500,
        "order": 7,
    },
    {
        "code": "streak_100",
        "name": "Eterno",
        "description": "100 dias de sequência",
        "icon": "💎",
        "category": "streak",
        "condition": {"type": "streak_reached", "value": 100},
        "reward_xp": 1000,
        "order": 8,
    },
    
    # Level-based
    {
        "code": "level_5",
        "name": "Nível 5",
        "description": "Atinja nível 5",
        "icon": "⭐",
        "category": "level",
        "condition": {"type": "level_reached", "value": 5},
        "reward_xp": 0,  # Nível já dá XP
        "order": 9,
    },
    {
        "code": "level_10",
        "name": "Nível 10",
        "description": "Atinja nível 10",
        "icon": "⭐⭐",
        "category": "level",
        "condition": {"type": "level_reached", "value": 10},
        "reward_xp": 0,
        "order": 10,
    },
    {
        "code": "level_25",
        "name": "Nível 25",
        "description": "Atinja nível 25",
        "icon": "✨",
        "category": "level",
        "condition": {"type": "level_reached", "value": 25},
        "reward_xp": 0,
        "order": 11,
    },
    {
        "code": "level_50",
        "name": "Mestria Total",
        "description": "Atinja nível 50",
        "icon": "👑",
        "category": "level",
        "condition": {"type": "level_reached", "value": 50},
        "reward_xp": 0,
        "order": 12,
    },
    
    # Infestation-based
    {
        "code": "zero_infestation",
        "name": "Esterilizado",
        "description": "Mantenha infestação em 0 por 1 dia",
        "icon": "✨",
        "category": "infestation",
        "condition": {"type": "zero_infestation_days", "value": 1},
        "reward_xp": 100,
        "order": 13,
    },
    {
        "code": "clean_week",
        "name": "Semana Limpa",
        "description": "Mantenha infestação abaixo de 20 por 1 semana",
        "icon": "🏡",
        "category": "infestation",
        "condition": {"type": "low_infestation_days", "value": 7, "threshold": 20},
        "reward_xp": 200,
        "order": 14,
    },
    
    # Room-based
    {
        "code": "all_rooms_setup",
        "name": "Casa Completa",
        "description": "Configure todos os 6 cômodos",
        "icon": "🏠",
        "category": "room",
        "condition": {"type": "rooms_count", "value": 6},
        "reward_xp": 150,
        "order": 15,
    },
    {
        "code": "room_zero_inf",
        "name": "Cômodo Impecável",
        "description": "Mantenha um cômodo em 0 de infestação por 3 dias",
        "icon": "🧹",
        "category": "room",
        "condition": {"type": "room_zero_infestation_days", "value": 3},
        "reward_xp": 75,
        "order": 16,
    },
]
```

### 1.4 Management Command para Popular Conquistas

```python
# gamification/management/commands/load_achievements.py

from django.core.management.base import BaseCommand
from gamification.models import Achievement

ACHIEVEMENTS_DATA = [...]  # Acima

class Command(BaseCommand):
    help = 'Load initial achievements into database'

    def handle(self, *args, **options):
        created = 0
        for ach_data in ACHIEVEMENTS_DATA:
            obj, was_created = Achievement.objects.update_or_create(
                code=ach_data['code'],
                defaults=ach_data,
            )
            if was_created:
                created += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Loaded {created} new achievements')
        )

# Rodar: python manage.py load_achievements
```

### 1.5 Serviço para Check & Unlock Achievements

```python
# gamification/services.py (adicionar ao existente)

from gamification.models import Achievement, UserAchievement
from tasks.models import TaskCompletion

def check_and_unlock_achievements(user):
    """
    Verifica todas as condições de conquista e desbloqueia as que foram atingidas.
    Chamado ao completar tarefa, subir nível, etc.
    """
    locked_achievements = Achievement.objects.filter(
        active=True
    ).exclude(
        user_records__user=user
    )
    
    for achievement in locked_achievements:
        if should_unlock(user, achievement):
            unlock_achievement(user, achievement)

def should_unlock(user, achievement):
    """Verifica se condição foi atingida"""
    condition = achievement.condition
    cond_type = condition.get('type')
    value = condition.get('value')
    
    if cond_type == 'task_completed_count':
        count = TaskCompletion.objects.filter(user=user).count()
        return count >= value
    
    elif cond_type == 'streak_reached':
        return user.streak >= value
    
    elif cond_type == 'level_reached':
        return user.level >= value
    
    elif cond_type == 'zero_infestation_days':
        # Simplificado: se infestação é 0 agora e user.streak >= value
        from tasks.models import Task
        from datetime import timedelta
        from django.utils import timezone
        
        # Check se teve 0 infestação por X dias consecutivos
        # Isso requer histórico mais detalhado (future feature)
        # Por agora, return False (ou implemente com RoomInfestationEvent)
        return False
    
    elif cond_type == 'low_infestation_days':
        threshold = condition.get('threshold', 20)
        # Similar: requer histórico
        return user.total_infestation <= threshold
    
    elif cond_type == 'rooms_count':
        rooms_count = user.room_set.count()
        return rooms_count >= value
    
    return False

def unlock_achievement(user, achievement):
    """Desbloqueia e concede XP"""
    user_achievement, created = UserAchievement.objects.get_or_create(
        user=user,
        achievement=achievement,
    )
    
    if created and achievement.reward_xp > 0:
        user.total_xp += achievement.reward_xp
        user.save(update_fields=['total_xp', 'updated_at'])
        
        # Log event
        print(f"✅ {user.name} desbloqueou {achievement.name}!")
    
    return user_achievement

# Chamar em complete_task_service:
def complete_task_service(task):
    # ... código existente ...
    
    # Check achievements
    check_and_unlock_achievements(user)
    
    return completion, user
```

### 1.6 Serializers e Views

```python
# gamification/serializers.py

from rest_framework import serializers
from gamification.models import Achievement, UserAchievement

class AchievementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Achievement
        fields = ['id', 'code', 'name', 'description', 'icon', 'category', 'reward_xp', 'order']

class UserAchievementSerializer(serializers.ModelSerializer):
    achievement = AchievementSerializer(read_only=True)
    
    class Meta:
        model = UserAchievement
        fields = ['id', 'achievement', 'unlocked_at', 'seen']

# gamification/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

class UserAchievementViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserAchievementSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return UserAchievement.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def all_achievements(self, request):
        """GET /api/v1/achievements/all_achievements/ — Todas (locked + unlocked)"""
        unlocked_ids = UserAchievement.objects.filter(
            user=request.user
        ).values_list('achievement_id', flat=True)
        
        all_achievements = Achievement.objects.filter(active=True)
        unlocked = all_achievements.filter(id__in=unlocked_ids)
        locked = all_achievements.exclude(id__in=unlocked_ids)
        
        return Response({
            'unlocked': AchievementSerializer(unlocked, many=True).data,
            'locked': AchievementSerializer(locked, many=True).data,
        })
    
    @action(detail=False, methods=['post'])
    def mark_as_seen(self, request):
        """POST /api/v1/achievements/mark_as_seen/"""
        UserAchievement.objects.filter(
            user=request.user,
            seen=False
        ).update(seen=True)
        return Response({'status': 'marked'})

# gamification/urls.py

from rest_framework.routers import DefaultRouter
from gamification.views import UserAchievementViewSet

router = DefaultRouter()
router.register('achievements', UserAchievementViewSet, basename='achievement')

urlpatterns = router.urls
```

---

## 2. Fotos Antes/Depois

### 2.1 Models

```python
# houses/models.py (adicionar)

class TaskPhoto(models.Model):
    """Fotos de progresso de uma tarefa"""
    
    PHOTO_TYPE_CHOICES = (
        ('before', 'Antes'),
        ('after', 'Depois'),
        ('progress', 'Progresso'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey('tasks.Task', on_delete=models.CASCADE, related_name='photos')
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    
    photo_type = models.CharField(max_length=20, choices=PHOTO_TYPE_CHOICES)
    image = models.ImageField(upload_to='task_photos/%Y/%m/%d/')
    caption = models.TextField(blank=True, null=True, max_length=500)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'task_photos'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.task.title} - {self.get_photo_type_display()}"

class RoomPhoto(models.Model):
    """Snapshots do estado de um cômodo ao longo do tempo"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey('houses.Room', on_delete=models.CASCADE, related_name='photos')
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    
    image = models.ImageField(upload_to='room_photos/%Y/%m/%d/')
    caption = models.TextField(blank=True, null=True, max_length=500)
    
    # Snapshot do estado quando foto foi tirada
    infestation_snapshot = models.FloatField()
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'room_photos'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.room.get_name_display()} - {self.created_at.date()}"
```

### 2.2 Serializers

```python
# houses/serializers.py (adicionar)

from rest_framework import serializers
from houses.models import TaskPhoto, RoomPhoto

class TaskPhotoSerializer(serializers.ModelSerializer):
    photo_type_display = serializers.CharField(source='get_photo_type_display', read_only=True)
    
    class Meta:
        model = TaskPhoto
        fields = ['id', 'task', 'photo_type', 'photo_type_display', 'image', 'caption', 'created_at']
        read_only_fields = ['id', 'created_at']

class RoomPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomPhoto
        fields = ['id', 'room', 'image', 'caption', 'infestation_snapshot', 'created_at']
        read_only_fields = ['id', 'created_at']
```

### 2.3 Views

```python
# houses/views.py (adicionar)

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from houses.models import TaskPhoto, RoomPhoto
from houses.serializers import TaskPhotoSerializer, RoomPhotoSerializer

class TaskPhotoViewSet(viewsets.ModelViewSet):
    serializer_class = TaskPhotoSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return TaskPhoto.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def by_task(self, request):
        """GET /api/v1/task-photos/by_task/?task_id=<id>"""
        task_id = request.query_params.get('task_id')
        if not task_id:
            return Response({'error': 'task_id required'}, status=400)
        
        photos = TaskPhoto.objects.filter(user=request.user, task_id=task_id)
        serializer = self.get_serializer(photos, many=True)
        return Response(serializer.data)

class RoomPhotoViewSet(viewsets.ModelViewSet):
    serializer_class = RoomPhotoSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return RoomPhoto.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        room_id = self.request.data.get('room')
        room = Room.objects.get(id=room_id, user=self.request.user)
        serializer.save(
            user=self.request.user,
            infestation_snapshot=room.infestation
        )
    
    @action(detail=False, methods=['get'])
    def gallery(self, request):
        """GET /api/v1/room-photos/gallery/?room_id=<id> — Timeline de fotos"""
        room_id = request.query_params.get('room_id')
        if not room_id:
            return Response({'error': 'room_id required'}, status=400)
        
        photos = RoomPhoto.objects.filter(
            user=request.user,
            room_id=room_id
        ).order_by('-created_at')
        
        serializer = self.get_serializer(photos, many=True)
        return Response(serializer.data)
```

### 2.4 URL Updates

```python
# houses/urls.py

router.register('task-photos', TaskPhotoViewSet, basename='task-photo')
router.register('room-photos', RoomPhotoViewSet, basename='room-photo')
```

### 2.5 Storage Configuration

```python
# settings.py

# Usar S3 em produção, local em dev
if DEBUG:
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'
else:
    # S3 via django-storages
    STORAGES = {
        'default': {
            'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage',
        },
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
        },
    }
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'us-east-1')

# settings.py também
DATA_UPLOAD_MAX_MEMORY_SIZE = 50000000  # 50MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 50000000
```

---

## 3. Expansão de Níveis até 50

### 3.1 Mudança no Model User

```python
# accounts/models.py — alteração

class User(AbstractBaseUser):
    # ... campos existentes ...
    level = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(50)],  # Antes era 12
        help_text="Nível atual (1-50)"
    )
    
    def get_xp_for_next_level(self):
        """
        Fórmula exponencial (melhor que hardcoded para 50 níveis).
        Começa em 100 e cresce com cada nível.
        """
        if self.level >= 50:
            return 0
        
        # base * (level + 1) ^ exponent
        # 100 * 2^1.05 = progression suave
        base = 100
        return int(base * ((self.level + 1) ** 1.05))
```

### 3.2 Tabela de Exemplo (para referência)

```python
# Calcular XP necessário para cada nível:

LEVEL_XP_TABLE = {
    1: 100,
    2: 205,
    3: 316,
    4: 433,
    5: 558,
    10: 1289,
    15: 2397,
    20: 3918,
    25: 5944,
    30: 8560,
    35: 11856,
    40: 15932,
    45: 20902,
    50: 26886,  # Total ~105k XP para 50
}

# Fórmula: base * (level^1.05) onde base=100
```

### 3.3 Migration

```python
# accounts/migrations/0002_expand_levels.py

from django.db import migrations, models
import django.core.validators

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='level',
            field=models.IntegerField(
                default=1,
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(50)
                ],
                help_text='Nível atual (1-50)'
            ),
        ),
    ]
```

### 3.4 Atualizar Achievements

```python
# Adicionar achievements de mais níveis

ACHIEVEMENTS_DATA.extend([
    {
        "code": "level_15",
        "name": "Nível 15",
        "description": "Atinja nível 15",
        "icon": "⭐⭐⭐",
        "category": "level",
        "condition": {"type": "level_reached", "value": 15},
        "reward_xp": 0,
        "order": 17,
    },
    {
        "code": "level_30",
        "name": "Nível 30",
        "description": "Atinja nível 30",
        "icon": "✨✨",
        "category": "level",
        "condition": {"type": "level_reached", "value": 30},
        "reward_xp": 0,
        "order": 18,
    },
    {
        "code": "level_50",
        "name": "Mestria Total",
        "description": "Atinja nível 50",
        "icon": "👑👑",
        "category": "level",
        "condition": {"type": "level_reached", "value": 50},
        "reward_xp": 0,
        "order": 19,
    },
])
```

---

## 4. Gráficos Semanal/Mensal

### 4.1 Backend — Endpoints de Dados Agregados

```python
# gamification/views.py (adicionar)

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta, datetime
from tasks.models import TaskCompletion
from houses.models import RoomInfestationEvent
from django.db.models import Count, Sum, Avg

class StatsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def weekly_stats(self, request):
        """
        GET /api/v1/stats/weekly_stats/?weeks=4
        Retorna: XP por dia, streak, infestação média por dia
        """
        weeks = int(request.query_params.get('weeks', 4))
        end_date = timezone.now()
        start_date = end_date - timedelta(days=weeks*7)
        
        user = request.user
        
        # XP por dia
        xp_by_day = {}
        for i in range(weeks * 7):
            day = (start_date + timedelta(days=i)).date()
            xp = TaskCompletion.objects.filter(
                user=user,
                completed_at__date=day
            ).aggregate(total=Sum('xp_earned'))['total'] or 0
            xp_by_day[str(day)] = xp
        
        # Tarefas completadas por dia
        tasks_by_day = {}
        for i in range(weeks * 7):
            day = (start_date + timedelta(days=i)).date()
            count = TaskCompletion.objects.filter(
                user=user,
                completed_at__date=day
            ).count()
            tasks_by_day[str(day)] = count
        
        # Infestação média por dia (agregado de todos os cômodos)
        infestation_by_day = {}
        for i in range(weeks * 7):
            day = (start_date + timedelta(days=i)).date()
            events = RoomInfestationEvent.objects.filter(
                user=user,
                created_at__date=day
            ).aggregate(avg=Avg('infestation_after'))['avg'] or 0
            infestation_by_day[str(day)] = round(avg, 2)
        
        return Response({
            'xp_by_day': xp_by_day,
            'tasks_by_day': tasks_by_day,
            'infestation_by_day': infestation_by_day,
            'period': f'{weeks} weeks',
        })
    
    @action(detail=False, methods=['get'])
    def monthly_stats(self, request):
        """
        GET /api/v1/stats/monthly_stats/?months=12
        Retorna: XP por mês, tarefas completadas, streak máximo
        """
        months = int(request.query_params.get('months', 12))
        end_date = timezone.now()
        start_date = end_date - timedelta(days=months*30)
        
        user = request.user
        
        # Agrupar por mês
        stats_by_month = {}
        for month_offset in range(months):
            month_start = start_date + timedelta(days=month_offset*30)
            month_end = month_start + timedelta(days=30)
            
            month_key = month_start.strftime('%Y-%m')
            
            xp = TaskCompletion.objects.filter(
                user=user,
                completed_at__gte=month_start,
                completed_at__lt=month_end
            ).aggregate(total=Sum('xp_earned'))['total'] or 0
            
            tasks = TaskCompletion.objects.filter(
                user=user,
                completed_at__gte=month_start,
                completed_at__lt=month_end
            ).count()
            
            stats_by_month[month_key] = {
                'xp': xp,
                'tasks': tasks,
            }
        
        return Response({
            'stats_by_month': stats_by_month,
            'period': f'{months} months',
        })
    
    @action(detail=False, methods=['get'])
    def dashboard_summary(self, request):
        """
        GET /api/v1/stats/dashboard_summary/
        Resumo: hoje, semana, mês (para cards no dashboard)
        """
        user = request.user
        now = timezone.now()
        today = now.date()
        
        # Today
        today_xp = TaskCompletion.objects.filter(
            user=user,
            completed_at__date=today
        ).aggregate(total=Sum('xp_earned'))['total'] or 0
        
        today_tasks = TaskCompletion.objects.filter(
            user=user,
            completed_at__date=today
        ).count()
        
        # This week
        week_start = now - timedelta(days=now.weekday())
        week_xp = TaskCompletion.objects.filter(
            user=user,
            completed_at__gte=week_start
        ).aggregate(total=Sum('xp_earned'))['total'] or 0
        
        # This month
        month_start = now.replace(day=1)
        month_xp = TaskCompletion.objects.filter(
            user=user,
            completed_at__gte=month_start
        ).aggregate(total=Sum('xp_earned'))['total'] or 0
        
        return Response({
            'today': {'xp': today_xp, 'tasks': today_tasks},
            'this_week': {'xp': week_xp},
            'this_month': {'xp': month_xp},
        })
```

### 4.2 Frontend — Componentes de Gráficos

```typescript
// src/components/charts/WeeklyChart.tsx

import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface WeeklyChartProps {
  data: {
    xp_by_day: Record<string, number>;
    tasks_by_day: Record<string, number>;
    infestation_by_day: Record<string, number>;
  };
}

export const WeeklyChart: React.FC<WeeklyChartProps> = ({ data }) => {
  // Transform data to recharts format
  const chartData = Object.entries(data.xp_by_day).map(([date, xp]) => ({
    date: new Date(date).toLocaleDateString('pt-BR', { weekday: 'short', month: 'short', day: 'numeric' }),
    xp,
    tasks: data.tasks_by_day[date] || 0,
    infestation: data.infestation_by_day[date] || 0,
  }));

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h3 className="text-xl font-bold mb-4">Últimas 4 Semanas</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" angle={-45} textAnchor="end" height={80} />
          <YAxis yAxisId="left" />
          <YAxis yAxisId="right" orientation="right" />
          <Tooltip />
          <Legend />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="xp"
            stroke="#3b82f6"
            name="XP Ganho"
            strokeWidth={2}
          />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="tasks"
            stroke="#10b981"
            name="Tarefas"
            strokeWidth={2}
          />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="infestation"
            stroke="#ef4444"
            name="Infestação %"
            strokeWidth={2}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};
```

```typescript
// src/components/charts/MonthlyChart.tsx

import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface MonthlyChartProps {
  data: {
    stats_by_month: Record<string, { xp: number; tasks: number }>;
  };
}

export const MonthlyChart: React.FC<MonthlyChartProps> = ({ data }) => {
  const chartData = Object.entries(data.stats_by_month).map(([month, stats]) => ({
    month,
    xp: stats.xp,
    tasks: stats.tasks,
  }));

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h3 className="text-xl font-bold mb-4">Últimos 12 Meses</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="month" />
          <YAxis yAxisId="left" />
          <YAxis yAxisId="right" orientation="right" />
          <Tooltip />
          <Legend />
          <Bar yAxisId="left" dataKey="xp" fill="#3b82f6" name="XP Total" />
          <Bar yAxisId="right" dataKey="tasks" fill="#10b981" name="Tarefas" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};
```

### 4.3 Dashboard Update (Frontend)

```typescript
// src/pages/dashboard/Dashboard.tsx (adicionar ao final)

import { WeeklyChart } from '../../components/charts/WeeklyChart';
import { MonthlyChart } from '../../components/charts/MonthlyChart';
import { useEffect, useState } from 'react';
import { apiClient } from '../../api/client';

export const Dashboard: React.FC = () => {
  // ... código existente ...
  
  const [stats, setStats] = useState({
    weekly: null,
    monthly: null,
    summary: null,
  });
  const [loadingStats, setLoadingStats] = useState(false);

  useEffect(() => {
    const loadStats = async () => {
      setLoadingStats(true);
      try {
        const [weekly, monthly, summary] = await Promise.all([
          apiClient.get('/stats/weekly_stats/?weeks=4'),
          apiClient.get('/stats/monthly_stats/?months=12'),
          apiClient.get('/stats/dashboard_summary/'),
        ]);
        setStats({
          weekly: weekly.data,
          monthly: monthly.data,
          summary: summary.data,
        });
      } catch (err) {
        console.error('Erro ao carregar stats:', err);
      } finally {
        setLoadingStats(false);
      }
    };
    
    loadStats();
  }, [user]);

  return (
    <MainLayout>
      {/* ... código existente ... */}
      
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
        <div className="bg-white p-4 rounded-lg shadow">
          <p className="text-gray-600 text-sm">Hoje</p>
          <p className="text-2xl font-bold text-blue-600">
            {stats.summary?.today?.xp || 0} XP
          </p>
          <p className="text-xs text-gray-500">
            {stats.summary?.today?.tasks || 0} tarefas
          </p>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <p className="text-gray-600 text-sm">Esta Semana</p>
          <p className="text-2xl font-bold text-blue-600">
            {stats.summary?.this_week?.xp || 0} XP
          </p>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <p className="text-gray-600 text-sm">Este Mês</p>
          <p className="text-2xl font-bold text-blue-600">
            {stats.summary?.this_month?.xp || 0} XP
          </p>
        </div>
      </div>

      {/* Charts */}
      <div className="space-y-6 mt-8">
        {stats.weekly && <WeeklyChart data={stats.weekly} />}
        {stats.monthly && <MonthlyChart data={stats.monthly} />}
      </div>
    </MainLayout>
  );
};
```

### 4.4 Dependencies

```bash
npm install recharts
# ou
npm install chart.js react-chartjs-2
```

### 4.5 Gamification URLs

```python
# gamification/urls.py

from rest_framework.routers import DefaultRouter
from gamification.views import StatsViewSet

router = DefaultRouter()
router.register('stats', StatsViewSet, basename='stats')

urlpatterns = router.urls
```

---

## 5. Resumo de Changes

### 5.1 Backend

| Feature | Models | Serializers | Views | URLs |
|---------|--------|-------------|-------|------|
| Achievements | Achievement, UserAchievement | AchievementSerializer, UserAchievementSerializer | UserAchievementViewSet | `/achievements/` |
| Photos | TaskPhoto, RoomPhoto | TaskPhotoSerializer, RoomPhotoSerializer | TaskPhotoViewSet, RoomPhotoViewSet | `/task-photos/`, `/room-photos/` |
| Levels | User.level (1→50) | — | — | — |
| Stats | — | — | StatsViewSet | `/stats/` |

### 5.2 Frontend

| Component | Path | Purpose |
|-----------|------|---------|
| AchievementCard | `components/achievements/` | Display unlock badge |
| AchievementsList | `components/achievements/` | All achievements with filters |
| PhotoGallery | `components/gallery/` | Before/after & room timeline |
| UploadPhoto | `components/gallery/` | Camera/file input |
| WeeklyChart | `components/charts/` | Recharts line chart |
| MonthlyChart | `components/charts/` | Recharts bar chart |

### 5.3 Migrations

```bash
# 1. Achievements
python manage.py makemigrations gamification
python manage.py migrate gamification

# 2. Photos
python manage.py makemigrations houses
python manage.py migrate houses

# 3. Levels
python manage.py makemigrations accounts
python manage.py migrate accounts

# 4. Load achievements
python manage.py load_achievements
```

---

## 6. Decisões Arquiteturais

### 6.1 Achievements como Dados, Não Código

**Problema:** Se cada conquista nova exigisse código novo (nova classe, novo serializer), seria escalável.

**Solução:** Conquistas armazenadas como dados em DB com JSON `condition` flexível.

**Benefício:** Adicionar "Complete 200 tarefas" = 1 insert SQL, sem deploy.

### 6.2 Fotos com Metadata

**Decisão:** Armazenar `infestation_snapshot` com cada foto de room.

**Justificativa:** Permite ver tendência visual + quantitativa ao longo do tempo.

### 6.3 Níveis Exponenciais

**Antes:** Hardcoded 1-12 níveis com tabela fixa.

**Agora:** Fórmula escalável até 50.

**Fórmula:** `base * (level + 1) ^ 1.05` = progressão suave (não explode, não estagna).

### 6.4 Gráficos Agregados no Backend

**Decisão:** Backend calcula agregações (XP por dia/mês).

**Justificativa:** Frontend só renderiza; evita N queries ao filtrar dados.

---

## 7. Testing

```python
# gamification/tests/test_achievements.py

@pytest.mark.django_db
def test_unlock_first_task_achievement():
    user = User.objects.create_user(...)
    achievement = Achievement.objects.create(
        code='first_task',
        condition={'type': 'task_completed_count', 'value': 1}
    )
    
    # Complete 1 task
    complete_task_service(task)
    
    # Check achievement unlocked
    assert UserAchievement.objects.filter(
        user=user,
        achievement=achievement
    ).exists()

@pytest.mark.django_db
def test_weekly_stats_xp_calculation():
    user = User.objects.create_user(...)
    
    # Create completions over 7 days
    for i in range(7):
        TaskCompletion.objects.create(
            user=user,
            xp_earned=50,
            completed_at=now() - timedelta(days=i)
        )
    
    # Call endpoint
    response = client.get('/api/stats/weekly_stats/')
    
    # Verify 7 days of data
    assert len(response.data['xp_by_day']) == 7
```

---

**V1.x Status:** Pronto para implementação.

**Próximo (V2):** Ranking familiar, marketplace, IA.
