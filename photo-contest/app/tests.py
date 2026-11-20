from django.test import TestCase
from django.db.models import Q
from .models import User


def run_orm_tests():
    # Все пользователи
    users = User.objects.all()
    print("ALL:", users)

    # Активные
    users = User.objects.filter(is_active=True)
    print("ACTIVE:", users)

    # Лукапы
    users = User.objects.filter(id__gt=5)
    print("ID > 5:", users)

    users = User.objects.filter(id__in=[1, 5, 8])
    print("ID in [1,5,8]:", users)

    users = User.objects.filter(username__icontains="user")
    print("LOGIN contains 'user':", users)

    users = User.objects.filter(username__startswith="test")
    print("LOGIN starts 'test':", users)

    users = User.objects.filter(avatar__isnull=True)
    print("NO avatar:", users)

    # Логика
    users = User.objects.filter(Q(is_active=True) | Q(role_id=3))
    print("OR:", users)

    users = User.objects.exclude(is_active=True, role_id=3)
    print("NOT exclude:", users)

    users = User.objects.exclude(Q(is_active=True) | Q(role_id=3))
    print("NOT (A or B):", users)


class OrmTestCase(TestCase):
    def test_run(self):
        run_orm_tests()