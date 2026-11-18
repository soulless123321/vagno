import os
import secrets
import uuid
import csv
from email.contentmanager import raw_data_manager
from fileinput import filename
from http.client import responses
from os import write
from pydoc import describe
from turtledemo.penrose import start
from venv import create

from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.middleware.csrf import get_token
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.contrib.auth.hashers import make_password, check_password
from django.template.defaultfilters import title
from django.template.defaulttags import comment
from django.utils.encoding import filepath_to_uri
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from django.urls import reverse
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from email.mime.image import MIMEImage
from datetime import datetime
from django.utils import timezone
from twisted.web.xmlrpc import payloadTemplate
from urllib3.util.connection import allowed_gai_family

from .models import User, Contest, Work, Vote, Comment


def generate_token(user, salt: str):

    if salt == 'api_access':
        payload = {
            'id_user': user.id
        }
    elif salt == 'ws_ticket':
        payload = {
            'id_user': user.id
        }
    elif salt == 'activation':
        payload = {
            'id_user': user.id,
            'email': user.email
        }

    else:
        return None
    signer = TimestampSigner(salt=salt)
    return signer.sign_object(payload, compress=True)


def get_user(token: str, salt: str):

    if salt == 'api_access':
        max_age = 900
    elif salt =='ws_ticket':
        max_age = 60
    elif salt == 'activation':
        max_age = 86400
    else:
        return None

    signer = TimestampSigner(salt=salt)
    try:
        payload = signer.unsign_object(token, max_age=max_age)
    except (BadSignature, SignatureExpired, ValueError, TypeError):
        return None

    id_user = payload.get('id_user')
    if not id_user:
        return None

    user = User.objects.filter(id=id_user).first()
    if not user:
        return None

    if salt == 'api_access':
        if not user.is_active:
            return None
        return user
    elif salt =='ws_ticket':
        if not user.is_active:
            return None
        return user
    elif salt == 'activation':
        token_email = payload.get('email')
        if user.email != token_email:
            return None
        return user

    return None


def send_activation_email(user, activation_link: str):
    subject = "Подтверждение регистрации. Mirro"

    context = {
        'name': user.username,
        'activation_link': activation_link
    }

    html_content = render_to_string('activation_email.html', context)
    text_content = strip_tags(html_content)

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email]
    )
    email.attach_alternative(html_content, "text/html")

    # === 1. Встроенная картинка (inline) ===
    logo_path = os.path.join(settings.BASE_DIR, 'app', 'static', 'images', 'logo.png')
    if os.path.exists(logo_path):
        with open(logo_path, 'rb') as f:
            logo_data = f.read()

        logo = MIMEImage(logo_data)
        logo.add_header('Content-ID', '<logo>')
        logo.add_header('Content-Disposition', 'inline', filename='logo.png')
        email.attach(logo)

    # === 2. Прикреплённый файл (attachment) ===
    attach_path = os.path.join(settings.BASE_DIR, 'app', 'static', 'files', 'welcome.docx')
    if os.path.exists(attach_path):
        with open(attach_path, 'rb') as f:
            file_data = f.read()
        email.attach(
            'welcome.docx',
            file_data,
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

    email.send(fail_silently=False)


def get_xcsrf(request):
    data = {
        'X-CSRFToken': get_token(request)
    }
    return JsonResponse(data, safe=False, status=200)


@csrf_exempt
def users(request):
    if request.method == 'POST':

        data = {}
        error422 = {
            "code": 422,
            "message": "Некорректные данные"
        }
        errors = {
            'name': [],
            'email': [],
            'password': [],
        }

        name = request.POST.get('name')
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Валидация имени
        if not name or ' ' in name:
            errors['name'].append('Поле не должно быть пустым или содержать пробелы')
        elif not name.isalpha() or not name.isascii():
            errors['name'].append('Имя должно состоять только из латинских букв')
        elif User.objects.filter(username=name).exists():
            errors['name'].append('Логин уже занят')

        # Валидация email
        if not email or '@' not in email:
            errors['email'].append('Введите корректный email')
        elif User.objects.filter(email=email).exists():
            errors['email'].append('Email уже зарегистрирован')

        # Валидация пароля
        if not password or len(password) < 8:
            errors['password'].append('Пароль должен содержать минимум 8 символов')
        elif not any(c.isdigit() for c in password):
            errors['password'].append('Пароль должен содержать хотя бы одну цифру')
        elif not any(c in '!@#$%^&*()_+-=' for c in password):
            errors['password'].append('Пароль должен содержать спецсимвол')

        for key in list(errors.keys()):
            if not errors[key]:
                del errors[key]

        if errors:
            error422['errors'] = errors
            return JsonResponse(error422, safe=False, status=422)

        hash_password = make_password(password)
        user = User(
            username=name,
            email=email,
            password=hash_password,
            is_active=False,
            role_id=2
        )
        user.save()

        # Генерируем токен активации и отправляем письмо
        activation_token = generate_token(user, 'activation')
        activation_link = request.build_absolute_uri(f"{reverse('email_confirm')}?token={activation_token}")
        send_activation_email(user, activation_link)
        print(f'ACTIVATION {activation_link}')

        data['user'] = {
            'id': user.id,
            'name': user.username,
            'email': user.email
        }

        return JsonResponse({'code': 201, "message": "Пользователь добавлен", "data": data}, safe=False, status=201)


@csrf_exempt
def email_confirm(request):
    if request.method == 'GET':
        token = request.GET.get('token')
        user = get_user(token, salt='activation')

        if not user:
            return JsonResponse({'code': 400, 'message': 'Ссылка недействительна или просрочена'}, status=400)

        user.is_active = True
        user.save()

        return JsonResponse({'code': 200, 'message': 'Почта успешно подтверждена!'}, status=200)


@csrf_exempt
def login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        if not email or not password:
            return JsonResponse({'code': 422, 'message': 'Введите email и пароль'}, safe=False, status=422)

        user = User.objects.filter(email=email).first()
        if not user or not check_password(password, user.password):
            return JsonResponse({'code': 401, 'message': 'Неверный email или пароль'}, safe=False, status=401)

        if not user.is_active:
            return JsonResponse({'code': 403, 'message': 'Аккаунт не активирован'}, safe=False, status=403)

        token = generate_token(user, salt='api_access')

        return JsonResponse({
            'code': 200,
            'message': 'Успешный вход',
            'data': {
                'token': token,
                'user': {
                    'id': user.id,
                    'name': user.username,
                    'email': user.email
                }
            }
        }, safe=False, status=200)


@csrf_exempt
def logout(request):
    return JsonResponse({'code': 200, 'message': 'Вы вышли из системы'}, safe=False, status=200)
#загрузка файлов
@csrf_exempt
def works(request):
    if request.method == 'POST':
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return JsonResponse({'code': 401, 'message': 'Токен не передан'}, status=401)

        parts = auth_header.split()
        if len(parts) != 2 or parts[0] != 'Bearer':
            return JsonResponse({'code': 401, 'message': 'Неверный формат токена'}, status=401)

        user = get_user(parts[1], salt='api_access')
        if not user:
            return JsonResponse({'code': 401, 'message': 'Токен недействителен или просрочен'}, status=401)

        contest_id = request.POST.get('contest_id')
        title = request.POST.get('title')
        image = request.FILES.get('image')

        if not contest_id or not title or not image:
            return JsonResponse({'code': 422, 'message': 'Заполните все поля'}, status=422)

        if image.size > 10 * 1024 * 1024:
            return JsonResponse({'code': 422, })
        allowed = ['image/jpeg', 'image/png', 'image/webp']
        if image.contest_type not in allowed:
            return JsonResponse({'code': 422, 'message': 'Только JPEG, PNG или WEBP'}, status=422)

        ext = image.name.split('.')[-1].lower()
        filename =f"{uuid.uuid4()}.{ext}"

        works_dir = os.path.join(settings.MEDIA_ROOT, 'works')
        os.makedirs(works_dir, exist_ok=True)

        filepath = os.path.join(works_dir, filename)
        with open(filepath, 'wb+') as f:
            for chunk in image.chunks():
                f.write(chunk)

        relative_path = f"works/{filename}"

        work = Work.objects.create(
            contest_id=int(contest_id),
            user_id=user.id,
            title=title,
            image=relative_path,
            status='pending',
            votes_count=0,
            views=0
        )

        return JsonResponse({
            'code': 201,
            'message': 'Работа загружена',
            'data': {
                'id': work.id,
                'title': work.title,
                'image': f"/media/{relative_path}",
                'status': work.status
            }
        }, status=201)
#функци для выгрузки аналитики по конкурсам
@csrf_exempt
def contests_analytics_csv(request):
    user = None
    auth_header = request.headers.get('Authorization')
    if auth_header and len(auth_header.split()) == 2:
        token = auth_header.split()[-1]
        user = get_user(token, 'api_access')

    if request.method != 'GET':
        return JsonResponse({'error': 'Метод не поддерживается'}, status=405)

    if not user:
        return JsonResponse({'code': 401, "message": "Пользователь не авторизован"}, status=401)

    if user.role_id not in (1, 3):
        return JsonResponse({'code': 403, "messsage": "Недостаточно прав"}, status=403)

    filename = 'contests_analytics.csv'
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response, delimiter=';')

    writer.writerow([
        'ID конкурса',
        'Название',
        'Статус',
        'Автор',
        'Email автора',
        'Кол-во работ',
        'Кол-во голосов',
        'Кол-во комментариев',
        'Дата создание'
    ])

    contests = Contest.objects.all().order_by('-id')
    for c in contests:
        author = User.objects.filter(id=c.created_by_id).first()
        author_name = author.username if author else 'Неизвестен'
        author_email =  author.email if author else '_'

        works = Work.objects.filter(contest_id=c.id)
        works_count = works.count()

        votes_count = Vote.objects.filter(contest_id=c.id).count()

        work_ids = list(works.values_list('id', flat=True))
        comments_count = Comment.objects.filter(work_id__in=work_ids).count()

        created_at = c.created_at.strftime('%Y-%m-%d %H:%M:%S') if c.created_at else ''

        writer.writerow([
            c.id,
            c.title,
            c.status,
            author_name,
            author_email,
            works_count,
            votes_count,
            comments_count,
            created_at
        ])

    return response
@csrf_exempt
@require_POST
def ws_ticket(request):
    user = None
    auth_header = request.header.get('Authorization')

    if auth_header and led (auth_header.split()) == 2:
        token = auth_header.split()[-1]
        user = get_user(token, 'api_access')

    if not user:
        return JsonResponse({'code': 401, 'message': 'Пользователь не авторизован'}, status=401)

    ticket = generate_token(user,salt='ws_ticket')
    if not ticket:
        return JsonResponse({'code': 500, 'error': 'Ошибка, тикет не создан'}, status=500)
    return JsonResponse({'ticket': ticket})
def main(request):
    return JsonResponse({'code': 200, 'message': 'API работает'}, safe=False, status=200)

def test(request):

    return HttpResponse ()

@csrf_exempt
def contests(request):
    if request.method == 'POST':
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return JsonResponse({'code': 401, 'message': 'Токен не передан'}, status=401)

        parts = auth_header.split()
        if len(parts) != 2 or parts[0] != 'Bearer':
            return JsonResponse({'code': 401, 'message': 'Неверный формат токена'}, status=401)

        user = get_user(parts[1], salt='api_access')
        if not user:
            return JsonResponse({'code': 401, 'message': 'Токен недействителен или просрочен'}, status=401)

        title = request.POST.get('title')

        if not title:
            return JsonResponse({'code': 422, 'message': 'Название обязательно'}, status=422)

        contest = Contest.objects.create(
            title=title,
            description=request.POST.get('describtion', ''),
            status='draft',
            submission_start=datetime.now(),
            submission_end=datetime.now(),
            voting_start=datetime.now(),
            voting_end=datetime.now(),
            created_by_id=user.id,
            comments_enabled=True,
            anonymous_voting=False
        )

        return JsonResponse({
            'code': 201,
            'message': 'Конкурс создан',
            'data': {
                'id': contest.id,
                'title': contest.title,
                'created_by': user.username
            }
        }, status=201)

    elif request.method == 'GET':

        auth_header = request.headers.get('Authorization')
        user = None

        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0] == 'Bearer':
                user = get_user(parts[1], salt='api_access')

        filter_param = request.GET.get('filter', 'all')

        if filter_param == 'mine':
            if not user:
                return JsonResponse({'code': 401, 'message': 'Пользователь не авторизован'}, status=401)
            queryset = Contest.objects.filter(created_by_id=user.id)
        elif filter_param == 'open':
            queryset = Contest.objects.filter(status='open')
        elif filter_param == 'voting':
            queryset = Contest.objects.filter(status='voting')
        elif filter_param == 'closed':
            queryset = Contest.objects.filter(status='closed')
        else:
            queryset = Contest.objects.all()

        if request.GET.get('sort') == 'title':
            queryset = queryset.order_by('title')
        else:
            queryset = queryset.order_by('-id')
        #пагинация
        try:
            page = int(request.GET.get('page', 1))
            per_page = int(request.GET.get('per_page', 10))
            if page < 1:
                page = 1
            if per_page <1:
                per_page = 10
        except (ValueError, TypeError):
            page = 1
            per_page = 10

        total = queryset.count()

        if total == 0:
            total_pages = 1
        else:
            total_pages = (total + per_page - 1) // per_page

        if page > total_pages:
            page = total_pages

        start = (page - 1) * per_page
        end = start + per_page
        queryset = queryset[start:end]

        contests_list = []
        for c in queryset:
            contests_list.append({
                'id': c.id,
                'title': c.title,
                'description': c.description,
                'status': c.status,
                'created_by_id': c.created_by_id,
                'created_at': c.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        return JsonResponse({
            'meta': {
                'page': page,
                'per_page': per_page
            },
            'data': contests_list
        },safe=False, status=200)

def generate_refresh_token(user):
    secret = secrets.token_urlsafe(64)
    user.token = make_password(secret)
    user.save(update_fields=['token'])
    return f'{user.pk_user}:{secret}'

def verify_refresh_token(raw):
    if not raw or ':' not in raw:
        return None
    id_user, secret = raw.split(':', 1)
    try:
        user = User.objects.filter(pk_user=id_user).first()
    except (ValueError, TypeError):
        return None
    if not user or not user.token:
        return None
    if not check_password(secret, user.token):
        return None
    if not user.is_active:
        return None
    return user
def revoke_refresh_token(user):
    user.token = None
    user.save(update_fields=['token'])
def logaut (request):
    data = request.GET.get('data')
    user = get_user(data['token'], 'api_access')
    if not user:
        return JsonResponse({'code': 200, 'message': 'Вы вышли'}, status=401)
    revoke_refresh_token(user)
    return JsonResponse({'code': 200,'message': 'Вы вышли'}, status=200)
@csrf_exempt
def auth_refresh(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Метод не поддерживается'}, status=405)
    raw = request.POST.get('token')
    user = verify_refresh_token(raw)
    if not user:
        return JsonResponse({'code': 401, 'message': 'Не авторизован'}, status=401)
    new_refresh = generate_refresh_token(user)
    new_access = generate_token(user, 'api_access')
    return  JsonResponse({
        'code': 200,
        'data': {
            'token': new_access,
            'refresh_token': new_refresh
        }
    }, status=200)
