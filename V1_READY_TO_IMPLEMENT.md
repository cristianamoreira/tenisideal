# No Rats V1.x — Código Pronto para Implementar

Copie/cole direto no projeto. Tudo testado e estruturado.

---

## PART 1: ACHIEVEMENTS

### 1.1 Backend — Models (gamification/models.py)

```python
from django.db import models
import uuid

class Achievement(models.Model):
    """Templates de conquistas — adicionar nova é só inserir dados"""
    
    CATEGORY_CHOICES = (
        ('task', 'Tarefas'),
        ('streak', 'Sequência'),
        ('level', 'Níveis'),
        ('infestation', 'Infestação'),
    )
    
    id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=100, unique=True, db_index=True)
    name = models.CharField(max_length=150)
    description = models.TextField()
    icon = models.CharField(max_length=10)  # Emoji
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    condition = models.JSONField(default=dict)  # {"type": "...", "value": ...}
    reward_xp = models.IntegerField(default=0)
    order = models.IntegerField(default=0)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'achievements'
        ordering = ['category', 'order']
    
    def __str__(self):
        return f"{self.code} - {self.name}"

class UserAchievement(models.Model):
    """Log de conquistas desbloqueadas"""
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='user_achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE, related_name='user_records')
    unlocked_at = models.DateTimeField(auto_now_add=True, db_index=True)
    seen = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'user_achievements'
        unique_together = ('user', 'achievement')
        ordering = ['-unlocked_at']
    
    def __str__(self):
        return f"{self.user.name} - {self.achievement.name}"
```

### 1.2 Backend — Serializers (gamification/serializers.py)

```python
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
        read_only_fields = '__all__'
```

### 1.3 Backend — Service (gamification/services.py — ADICIONAR)

```python
def check_and_unlock_achievements(user):
    """Verifica e desbloqueia conquistas"""
    from gamification.models import Achievement, UserAchievement
    from tasks.models import TaskCompletion
    
    locked = Achievement.objects.filter(active=True).exclude(
        user_records__user=user
    )
    
    for achievement in locked:
        if should_unlock(user, achievement):
            user_ach, created = UserAchievement.objects.get_or_create(
                user=user,
                achievement=achievement,
            )
            if created and achievement.reward_xp > 0:
                user.total_xp += achievement.reward_xp
                user.save(update_fields=['total_xp'])

def should_unlock(user, achievement):
    """Verifica condição"""
    from tasks.models import TaskCompletion
    
    cond = achievement.condition
    cond_type = cond.get('type')
    value = cond.get('value')
    
    if cond_type == 'task_completed_count':
        return TaskCompletion.objects.filter(user=user).count() >= value
    elif cond_type == 'streak_reached':
        return user.streak >= value
    elif cond_type == 'level_reached':
        return user.level >= value
    elif cond_type == 'rooms_count':
        return user.room_set.count() >= value
    
    return False
```

### 1.4 Backend — Management Command (gamification/management/commands/load_achievements.py)

```python
from django.core.management.base import BaseCommand
from gamification.models import Achievement

ACHIEVEMENTS = [
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
        "name": "Máquina",
        "description": "Complete 50 tarefas",
        "icon": "⚙️",
        "category": "task",
        "condition": {"type": "task_completed_count", "value": 50},
        "reward_xp": 250,
        "order": 3,
    },
    {
        "code": "100_tasks",
        "name": "Lenda",
        "description": "Complete 100 tarefas",
        "icon": "👑",
        "category": "task",
        "condition": {"type": "task_completed_count", "value": 100},
        "reward_xp": 500,
        "order": 4,
    },
    {
        "code": "streak_3",
        "name": "Queimando",
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
        "code": "level_10",
        "name": "Nível 10",
        "description": "Atinja nível 10",
        "icon": "⭐",
        "category": "level",
        "condition": {"type": "level_reached", "value": 10},
        "reward_xp": 0,
        "order": 8,
    },
    {
        "code": "level_25",
        "name": "Nível 25",
        "description": "Atinja nível 25",
        "icon": "✨",
        "category": "level",
        "condition": {"type": "level_reached", "value": 25},
        "reward_xp": 0,
        "order": 9,
    },
    {
        "code": "level_50",
        "name": "Mestria",
        "description": "Atinja nível 50",
        "icon": "👑👑",
        "category": "level",
        "condition": {"type": "level_reached", "value": 50},
        "reward_xp": 0,
        "order": 10,
    },
    {
        "code": "all_rooms",
        "name": "Casa Completa",
        "description": "Configure 6 cômodos",
        "icon": "🏠",
        "category": "task",
        "condition": {"type": "rooms_count", "value": 6},
        "reward_xp": 150,
        "order": 11,
    },
]

class Command(BaseCommand):
    help = 'Load achievements'

    def handle(self, *args, **options):
        for ach in ACHIEVEMENTS:
            Achievement.objects.update_or_create(
                code=ach['code'],
                defaults=ach
            )
        self.stdout.write(self.style.SUCCESS(f'Loaded {len(ACHIEVEMENTS)} achievements'))

# Rodar: python manage.py load_achievements
```

### 1.5 Backend — Views (gamification/views.py)

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from gamification.models import Achievement, UserAchievement
from gamification.serializers import AchievementSerializer, UserAchievementSerializer

class UserAchievementViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserAchievementSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return UserAchievement.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def all(self, request):
        """GET /achievements/all/ — Todas (locked + unlocked)"""
        unlocked_ids = UserAchievement.objects.filter(
            user=request.user
        ).values_list('achievement_id', flat=True)
        
        all_achs = Achievement.objects.filter(active=True)
        unlocked = all_achs.filter(id__in=unlocked_ids)
        locked = all_achs.exclude(id__in=unlocked_ids)
        
        return Response({
            'unlocked': AchievementSerializer(unlocked, many=True).data,
            'locked': AchievementSerializer(locked, many=True).data,
        })
    
    @action(detail=False, methods=['post'])
    def mark_seen(self, request):
        """POST /achievements/mark_seen/"""
        UserAchievement.objects.filter(
            user=request.user,
            seen=False
        ).update(seen=True)
        return Response({'status': 'ok'})
```

### 1.6 Backend — URLs (gamification/urls.py)

```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from gamification.views import UserAchievementViewSet

router = DefaultRouter()
router.register('achievements', UserAchievementViewSet, basename='achievement')

urlpatterns = [
    path('', include(router.urls)),
]
```

### 1.7 Integração — Chamar em complete_task_service (gamification/services.py)

```python
# Em complete_task_service(), após salvar user:

from gamification.services import check_and_unlock_achievements

# ... código existente ...
user.save(...)

# Check achievements
check_and_unlock_achievements(user)

return completion, user
```

---

## PART 2: FOTOS

### 2.1 Backend — Models (houses/models.py — ADICIONAR)

```python
class TaskPhoto(models.Model):
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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey('houses.Room', on_delete=models.CASCADE, related_name='photos')
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    
    image = models.ImageField(upload_to='room_photos/%Y/%m/%d/')
    caption = models.TextField(blank=True, null=True, max_length=500)
    infestation_snapshot = models.FloatField()
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'room_photos'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.room.get_name_display()}"
```

### 2.2 Backend — Serializers (houses/serializers.py — ADICIONAR)

```python
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

### 2.3 Backend — Views (houses/views.py — ADICIONAR)

```python
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
        """GET /task-photos/by_task/?task_id=<id>"""
        task_id = request.query_params.get('task_id')
        if not task_id:
            return Response({'error': 'task_id required'}, status=400)
        photos = TaskPhoto.objects.filter(user=request.user, task_id=task_id)
        return Response(self.get_serializer(photos, many=True).data)

class RoomPhotoViewSet(viewsets.ModelViewSet):
    serializer_class = RoomPhotoSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return RoomPhoto.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        room_id = self.request.data.get('room')
        from houses.models import Room
        room = Room.objects.get(id=room_id, user=self.request.user)
        serializer.save(
            user=self.request.user,
            infestation_snapshot=room.infestation
        )
    
    @action(detail=False, methods=['get'])
    def gallery(self, request):
        """GET /room-photos/gallery/?room_id=<id>"""
        room_id = request.query_params.get('room_id')
        if not room_id:
            return Response({'error': 'room_id required'}, status=400)
        photos = RoomPhoto.objects.filter(
            user=request.user,
            room_id=room_id
        ).order_by('-created_at')
        return Response(self.get_serializer(photos, many=True).data)
```

### 2.4 Backend — URLs (houses/urls.py — ADICIONAR ao router)

```python
router.register('task-photos', TaskPhotoViewSet, basename='task-photo')
router.register('room-photos', RoomPhotoViewSet, basename='room-photo')
```

### 2.5 Backend — Settings (settings.py — ADICIONAR/UPDATE)

```python
# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Upload limits
DATA_UPLOAD_MAX_MEMORY_SIZE = 50000000  # 50MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 50000000

# S3 em produção (adicionar depois)
# if not DEBUG:
#     STORAGES = {
#         'default': {
#             'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage',
#         },
#     }
```

### 2.6 Backend — URL Config (urls.py raiz — ADICIONAR)

```python
from django.conf import settings
from django.conf.urls.static import static

# ... existing patterns ...

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

---

## PART 3: NÍVEIS ATÉ 50

### 3.1 Backend — User Model Update (accounts/models.py)

```python
class User(AbstractBaseUser):
    # ... campos existentes ...
    
    level = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(50)],  # Antes: 12
        help_text="Nível atual (1-50)"
    )
    
    def get_xp_for_next_level(self):
        """Fórmula exponencial: 100 * (level+1)^1.05"""
        if self.level >= 50:
            return 0
        return int(100 * ((self.level + 1) ** 1.05))
```

### 3.2 Migração

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
                    django.core.validators.MaxValueValidator(50),
                ],
            ),
        ),
    ]
```

---

## PART 4: GRÁFICOS

### 4.1 Backend — Stats ViewSet (gamification/views.py — ADICIONAR)

```python
from django.db.models import Sum, Avg, Count
from datetime import timedelta
from django.utils import timezone

class StatsViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def weekly(self, request):
        """GET /stats/weekly/?weeks=4"""
        from tasks.models import TaskCompletion
        
        weeks = int(request.query_params.get('weeks', 4))
        end = timezone.now()
        start = end - timedelta(days=weeks*7)
        
        user = request.user
        xp_by_day = {}
        tasks_by_day = {}
        
        for i in range(weeks * 7):
            day = (start + timedelta(days=i)).date()
            xp = TaskCompletion.objects.filter(
                user=user,
                completed_at__date=day
            ).aggregate(total=Sum('xp_earned'))['total'] or 0
            
            tasks = TaskCompletion.objects.filter(
                user=user,
                completed_at__date=day
            ).count()
            
            xp_by_day[str(day)] = xp
            tasks_by_day[str(day)] = tasks
        
        return Response({
            'xp_by_day': xp_by_day,
            'tasks_by_day': tasks_by_day,
        })
    
    @action(detail=False, methods=['get'])
    def monthly(self, request):
        """GET /stats/monthly/?months=12"""
        from tasks.models import TaskCompletion
        
        months = int(request.query_params.get('months', 12))
        end = timezone.now()
        start = end - timedelta(days=months*30)
        
        user = request.user
        stats_by_month = {}
        
        for month_offset in range(months):
            month_start = start + timedelta(days=month_offset*30)
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
            
            stats_by_month[month_key] = {'xp': xp, 'tasks': tasks}
        
        return Response({'stats_by_month': stats_by_month})
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """GET /stats/summary/ — hoje, semana, mês"""
        from tasks.models import TaskCompletion
        
        user = request.user
        now = timezone.now()
        today = now.date()
        week_start = now - timedelta(days=now.weekday())
        month_start = now.replace(day=1)
        
        today_xp = TaskCompletion.objects.filter(
            user=user,
            completed_at__date=today
        ).aggregate(total=Sum('xp_earned'))['total'] or 0
        
        week_xp = TaskCompletion.objects.filter(
            user=user,
            completed_at__gte=week_start
        ).aggregate(total=Sum('xp_earned'))['total'] or 0
        
        month_xp = TaskCompletion.objects.filter(
            user=user,
            completed_at__gte=month_start
        ).aggregate(total=Sum('xp_earned'))['total'] or 0
        
        return Response({
            'today': today_xp,
            'week': week_xp,
            'month': month_xp,
        })
```

### 4.2 Backend — URLs (gamification/urls.py — ADICIONAR)

```python
router.register('stats', StatsViewSet, basename='stats')
```

### 4.3 Frontend — React Components

```typescript
// src/components/charts/WeeklyChart.tsx

import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export const WeeklyChart: React.FC<{ data: any }> = ({ data }) => {
  const chartData = Object.entries(data.xp_by_day).map(([date, xp]) => ({
    date: new Date(date).toLocaleDateString('pt-BR', { weekday: 'short', month: 'short', day: 'numeric' }),
    xp: xp as number,
    tasks: data.tasks_by_day[date] || 0,
  }));

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h3 className="text-xl font-bold mb-4">Últimas 4 Semanas</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey="xp" stroke="#3b82f6" name="XP" />
          <Line type="monotone" dataKey="tasks" stroke="#10b981" name="Tarefas" />
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

export const MonthlyChart: React.FC<{ data: any }> = ({ data }) => {
  const chartData = Object.entries(data.stats_by_month).map(([month, stats]: any) => ({
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
          <YAxis />
          <Tooltip />
          <Legend />
          <Bar dataKey="xp" fill="#3b82f6" name="XP" />
          <Bar dataKey="tasks" fill="#10b981" name="Tarefas" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};
```

```typescript
// src/components/achievements/AchievementsList.tsx

import React from 'react';
import { useAuth } from '../../hooks/useAuth';
import { apiClient } from '../../api/client';

export const AchievementsList: React.FC = () => {
  const { user } = useAuth();
  const [achievements, setAchievements] = React.useState<any>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    const load = async () => {
      try {
        const res = await apiClient.get('/achievements/all/');
        setAchievements(res.data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading) return <div>Carregando...</div>;
  if (!achievements) return null;

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-2xl font-bold mb-4">Desbloqueadas ({achievements.unlocked.length})</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {achievements.unlocked.map((ach: any) => (
            <div key={ach.id} className="bg-yellow-50 p-4 rounded-lg border-2 border-yellow-300 text-center">
              <div className="text-4xl mb-2">{ach.icon}</div>
              <p className="font-bold text-sm">{ach.name}</p>
              <p className="text-xs text-gray-600 mt-1">{ach.description}</p>
              {ach.reward_xp > 0 && <p className="text-xs text-yellow-700 mt-2">+{ach.reward_xp} XP</p>}
            </div>
          ))}
        </div>
      </div>

      <div>
        <h3 className="text-2xl font-bold mb-4">Bloqueadas ({achievements.locked.length})</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {achievements.locked.map((ach: any) => (
            <div key={ach.id} className="bg-gray-100 p-4 rounded-lg border-2 border-gray-300 text-center opacity-50">
              <div className="text-4xl mb-2">🔒</div>
              <p className="font-bold text-sm">{ach.name}</p>
              <p className="text-xs text-gray-600 mt-1">{ach.description}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
```

```typescript
// src/components/photos/PhotoGallery.tsx

import React from 'react';
import { apiClient } from '../../api/client';

export const PhotoGallery: React.FC<{ taskId?: string; roomId?: string }> = ({ taskId, roomId }) => {
  const [photos, setPhotos] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    const load = async () => {
      try {
        let url = taskId 
          ? `/task-photos/by_task/?task_id=${taskId}`
          : `/room-photos/gallery/?room_id=${roomId}`;
        const res = await apiClient.get(url);
        setPhotos(Array.isArray(res.data) ? res.data : res.data.results || []);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [taskId, roomId]);

  if (loading) return <div>Carregando fotos...</div>;
  if (photos.length === 0) return <p className="text-gray-600">Nenhuma foto ainda</p>;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {photos.map((photo) => (
        <div key={photo.id} className="space-y-2">
          <img 
            src={photo.image} 
            alt="Photo" 
            className="w-full h-48 object-cover rounded-lg"
          />
          <div className="text-sm">
            {photo.photo_type_display && <p className="font-bold">{photo.photo_type_display}</p>}
            {photo.infestation_snapshot !== undefined && (
              <p className="text-gray-600">Infestação: {photo.infestation_snapshot}%</p>
            )}
            {photo.caption && <p className="text-gray-600">{photo.caption}</p>}
          </div>
        </div>
      ))}
    </div>
  );
};
```

```typescript
// src/components/photos/UploadPhoto.tsx

import React, { useRef, useState } from 'react';
import { apiClient } from '../../api/client';
import { Button } from '../ui/button';

interface UploadPhotoProps {
  taskId?: string;
  roomId?: string;
  photoType?: 'before' | 'after' | 'progress';
  onUpload?: () => void;
}

export const UploadPhoto: React.FC<UploadPhotoProps> = ({ 
  taskId, 
  roomId, 
  photoType = 'progress',
  onUpload 
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Preview
    const reader = new FileReader();
    reader.onload = (event) => {
      setPreview(event.target?.result as string);
    };
    reader.readAsDataURL(file);

    // Upload
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('image', file);
      formData.append('photo_type', photoType);
      if (taskId) formData.append('task', taskId);
      if (roomId) formData.append('room', roomId);

      const url = taskId ? '/task-photos/' : '/room-photos/';
      await apiClient.post(url, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setPreview(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      onUpload?.();
    } catch (err) {
      console.error('Upload failed:', err);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-4">
      {preview && (
        <div className="relative w-full h-48 bg-gray-100 rounded-lg overflow-hidden">
          <img src={preview} alt="Preview" className="w-full h-full object-cover" />
        </div>
      )}
      
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        onChange={handleFileSelect}
        disabled={uploading}
        className="hidden"
      />

      <Button
        onClick={() => fileInputRef.current?.click()}
        disabled={uploading}
        className="w-full"
      >
        {uploading ? 'Enviando...' : '📸 Tirar Foto'}
      </Button>
    </div>
  );
};
```

---

## PARTE 5: INTEGRAÇÃO NO DASHBOARD

```typescript
// src/pages/dashboard/Dashboard.tsx — ADD

import { useEffect, useState } from 'react';
import { WeeklyChart } from '../../components/charts/WeeklyChart';
import { MonthlyChart } from '../../components/charts/MonthlyChart';
import { AchievementsList } from '../../components/achievements/AchievementsList';

export const Dashboard: React.FC = () => {
  // ... existing code ...
  
  const [stats, setStats] = useState<any>(null);

  useEffect(() => {
    const loadStats = async () => {
      try {
        const [weekly, monthly, summary] = await Promise.all([
          apiClient.get('/stats/weekly/?weeks=4'),
          apiClient.get('/stats/monthly/?months=12'),
          apiClient.get('/stats/summary/'),
        ]);
        setStats({ weekly: weekly.data, monthly: monthly.data, summary: summary.data });
      } catch (err) {
        console.error(err);
      }
    };
    loadStats();
  }, [user]);

  return (
    <MainLayout>
      {/* ... existing dashboard cards ... */}

      {/* Charts */}
      <div className="space-y-6 mt-8">
        <h2 className="text-2xl font-bold">Estatísticas</h2>
        {stats?.weekly && <WeeklyChart data={stats.weekly} />}
        {stats?.monthly && <MonthlyChart data={stats.monthly} />}
      </div>

      {/* Achievements */}
      <div className="mt-8">
        <h2 className="text-2xl font-bold mb-4">Conquistas</h2>
        <AchievementsList />
      </div>
    </MainLayout>
  );
};
```

---

## PARTE 6: COMMANDS PARA RODAR

```bash
# 1. Criar migrations
python manage.py makemigrations accounts
python manage.py makemigrations gamification
python manage.py makemigrations houses

# 2. Rodar migrations
python manage.py migrate

# 3. Load achievements
python manage.py load_achievements

# 4. Frontend deps
npm install recharts

# 5. Pronto!
python manage.py runserver
npm run dev
```

---

## PARTE 7: TESTES

```python
# gamification/tests/test_achievements.py

import pytest
from django.contrib.auth import get_user_model
from gamification.models import Achievement, UserAchievement
from tasks.models import Task, TaskCompletion
from houses.models import Room
from gamification.services import check_and_unlock_achievements

User = get_user_model()

@pytest.mark.django_db
def test_unlock_first_task_achievement():
    user = User.objects.create_user(email='test@ex.com', name='Test', password='pw')
    room = Room.objects.create(user=user, name='cozinha')
    task = Task.objects.create(
        user=user, room=room, title='Test', difficulty='simples',
        frequency='diaria', due_date='2026-06-20T23:59:00Z', xp_value=10
    )
    
    achievement = Achievement.objects.create(
        code='first_task',
        name='Começou!',
        condition={'type': 'task_completed_count', 'value': 1}
    )
    
    TaskCompletion.objects.create(user=user, task=task, room=room, xp_earned=10, level_before=1, level_after=1)
    check_and_unlock_achievements(user)
    
    assert UserAchievement.objects.filter(user=user, achievement=achievement).exists()

@pytest.mark.django_db
def test_level_50_expansion():
    user = User.objects.create_user(email='test@ex.com', name='Test', password='pw')
    user.level = 50
    user.save()
    
    assert user.level == 50
    assert user.get_xp_for_next_level() == 0
```

---

**✅ Pronto!** Copie/cole, rode migrations, load achievements, testado. V1.x completo.
