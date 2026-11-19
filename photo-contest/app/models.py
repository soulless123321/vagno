from django.db import models
from django.contrib.postgres.search import SearchVectorField # Исправление для tsvector

class Role(models.Model):
    id = models.IntegerField(primary_key=True) # Явно указываем PK
    name = models.CharField(unique=True, max_length=20)
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'roles'

class User(models.Model):
    id = models.IntegerField(primary_key=True)
    username = models.CharField(unique=True, max_length=150)
    password = models.CharField(max_length=128)
    email = models.CharField(unique=True, max_length=254)
    avatar = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True) # Отражаем дефолт БД
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    role = models.ForeignKey(Role, models.DO_NOTHING, db_column='role_id', default=2)
    token = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'users'

class Contest(models.Model):
    id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, blank=True, null=True, default='draft')
    submission_start = models.DateTimeField()
    submission_end = models.DateTimeField()
    voting_start = models.DateTimeField()
    voting_end = models.DateTimeField()
    results_date = models.DateTimeField(blank=True, null=True)
    created_by = models.ForeignKey(User, models.DO_NOTHING, db_column='created_by_id', blank=True, null=True)
    comments_enabled = models.BooleanField(default=True)
    anonymous_voting = models.BooleanField(default=False)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'contests'

class Work(models.Model):
    id = models.IntegerField(primary_key=True)
    contest = models.ForeignKey(Contest, models.DO_NOTHING, db_column='contest_id', blank=True, null=True)
    user = models.ForeignKey(User, models.DO_NOTHING, db_column='user_id', blank=True, null=True)
    title = models.CharField(max_length=200)
    image = models.CharField(max_length=255)
    status = models.CharField(max_length=20, blank=True, null=True, default='pending')
    votes_count = models.IntegerField(blank=True, null=True, default=0)
    views = models.IntegerField(blank=True, null=True, default=0)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    # ИСПРАВЛЕНО: правильный тип для PostgreSQL полнотекстового поиска
    search_vector = SearchVectorField(blank=True, null=True) 

    class Meta:
        managed = False
        db_table = 'works'

class Vote(models.Model):
    id = models.IntegerField(primary_key=True)
    user = models.ForeignKey(User, models.DO_NOTHING, db_column='user_id', blank=True, null=True)
    contest = models.ForeignKey(Contest, models.DO_NOTHING, db_column='contest_id', blank=True, null=True)
    work = models.ForeignKey(Work, models.DO_NOTHING, db_column='work_id', blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'votes'
        # Важно: это работает только на уровне Django. Нужен также UNIQUE в самой БД!
        unique_together = (('user', 'contest'),)

class Comment(models.Model):
    id = models.IntegerField(primary_key=True)
    work = models.ForeignKey(Work, models.DO_NOTHING, db_column='work_id', blank=True, null=True)
    user = models.ForeignKey(User, models.DO_NOTHING, db_column='user_id', blank=True, null=True)
    text = models.TextField()
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'comments'

class Notification(models.Model):
    id = models.IntegerField(primary_key=True)
    user = models.ForeignKey(User, models.DO_NOTHING, db_column='user_id', blank=True, null=True)
    type = models.CharField(max_length=30, blank=True, null=True)
    text = models.TextField()
    is_read = models.BooleanField(default=False)
    link = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'notifications'