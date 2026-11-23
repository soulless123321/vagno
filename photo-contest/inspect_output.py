# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Users(models.Model):
    username = models.CharField(unique=True, max_length=150)
    password = models.CharField(max_length=128)
    email = models.CharField(unique=True, max_length=254)
    avatar = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    role = models.ForeignKey('Roles', models.DB_SET_DEFAULT)
    token = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'users'


class Roles(models.Model):
    name = models.CharField(unique=True, max_length=20)
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'roles'


class Contests(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, blank=True, null=True)
    submission_start = models.DateTimeField()
    submission_end = models.DateTimeField()
    voting_start = models.DateTimeField()
    voting_end = models.DateTimeField()
    results_date = models.DateTimeField(blank=True, null=True)
    created_by = models.ForeignKey(Users, models.DB_CASCADE, blank=True, null=True)
    comments_enabled = models.BooleanField(blank=True, null=True)
    anonymous_voting = models.BooleanField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'contests'


class Works(models.Model):
    contest = models.ForeignKey(Contests, models.DB_CASCADE, blank=True, null=True)
    user = models.ForeignKey(Users, models.DB_CASCADE, blank=True, null=True)
    title = models.CharField(max_length=200)
    image = models.CharField(max_length=255)
    status = models.CharField(max_length=20, blank=True, null=True)
    votes_count = models.IntegerField(blank=True, null=True)
    views = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    search_vector = models.TextField(blank=True, null=True)  # This field type is a guess.

    class Meta:
        managed = False
        db_table = 'works'


class Votes(models.Model):
    user = models.ForeignKey(Users, models.DB_CASCADE, blank=True, null=True)
    contest = models.ForeignKey(Contests, models.DB_CASCADE, blank=True, null=True)
    work = models.ForeignKey(Works, models.DB_CASCADE, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'votes'
        unique_together = (('user', 'contest'),)


class Comments(models.Model):
    work = models.ForeignKey(Works, models.DB_CASCADE, blank=True, null=True)
    user = models.ForeignKey(Users, models.DB_CASCADE, blank=True, null=True)
    text = models.TextField()
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'comments'


class Notifications(models.Model):
    user = models.ForeignKey(Users, models.DB_CASCADE, blank=True, null=True)
    type = models.CharField(max_length=30, blank=True, null=True)
    text = models.TextField()
    is_read = models.BooleanField(blank=True, null=True)
    link = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'notifications'
