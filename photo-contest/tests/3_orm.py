import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nn_project.settings')
django.setup()

from django.db.models import Count
from app.models import User, Contest, Work


# 1. Сначала выбираю только ID активных пользователей через values_list.
#    Потом по этим ID получаю полные объекты через filter(id__in=ids).
ids = User.objects.filter(is_active=True).values_list('id', flat=True)
print('ids:', list(ids))

users = User.objects.filter(id__in=ids)
for u in users:
    print(u.id, u.username, u.email)


# 2. Группирую работы по конкурсу и считаю количество в каждой группе.
#    Через values_list забираю только ID конкурсов, где есть работы,
#    и потом получаю сами объекты конкурсов.
ids = Work.objects.values('contest_id').annotate(cnt=Count('id')).values_list('contest_id', flat=True)
print('ids:', list(ids))

contests = Contest.objects.filter(id__in=ids)
for c in contests:
    print(c.id, c.title)


# 3. То же самое, что во втором, но с фильтром после annotate.
#    Это HAVING в SQL — оставляет только конкурсы, где работ больше одной.
ids = Work.objects.values('contest_id').annotate(cnt=Count('id')).filter(cnt__gt=1).values_list('contest_id', flat=True)
print('ids:', list(ids))

contests = Contest.objects.filter(id__in=ids)
for c in contests:
    print(c.id, c.title)


# 4. WHERE + GROUP BY + HAVING в одном запросе.
#    Сначала filter до annotate — это WHERE (берём только одобренные работы).
#    Потом values + annotate — это GROUP BY (группируем по конкурсу и считаем).
#    И filter после annotate — это HAVING (оставляем конкурсы, где одобренных работ больше одной).
stats = (Work.objects.filter(status='approved').values('contest_id').annotate(cnt=Count('id')).filter(cnt__gt=1))
for row in stats:
    print(row['contest_id'], row['cnt'])