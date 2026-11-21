import os
import secrets
import uuid
import csv

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
                    'email': user.email,
                    'role_id': user.role_id
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

        # === ДОБАВЛЕННАЯ ПРОВЕРКА: существует ли конкурс и открыт ли он ===
        try:
            contest = Contest.objects.get(id=int(contest_id))
        except (Contest.DoesNotExist, ValueError, TypeError):
            return JsonResponse({'code': 404, 'message': 'Конкурс не найден'}, status=404)

        if contest.status != 'open':
            return JsonResponse({'code': 403, 'message': 'Конкурс не принимает работы (статус должен быть "open")'},
                                status=403)
        # ====================================================================

        if image.size > 10 * 1024 * 1024:
            return JsonResponse({'code': 422, 'message': 'Файл слишком большой (макс. 10 МБ)'}, status=422)

        allowed = ['image/jpeg', 'image/png', 'image/webp']
        if image.content_type not in allowed:
            return JsonResponse({'code': 422, 'message': 'Только JPEG, PNG или WEBP'}, status=422)

        ext = image.name.split('.')[-1].lower()
        filename = f"{uuid.uuid4()}.{ext}"

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
            'message': 'Работа загружена и отправлена на модерацию',
            'data': {
                'id': work.id,
                'title': work.title,
                'image': f"/media/{relative_path}",
                'status': work.status
            }
        }, status=201)

    elif request.method == 'GET':
        contest_id = request.GET.get('contest_id')
        status_param = request.GET.get('status', 'approved')
        mine = request.GET.get('mine', '').lower() == 'true'

        auth_header = request.headers.get('Authorization')
        current_user = None
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0] == 'Bearer':
                current_user = get_user(parts[1], salt='api_access')

        if mine:
            if not current_user:
                return JsonResponse({'code': 401, 'message': 'Пользователь не авторизован'}, status=401)
            queryset = Work.objects.filter(user_id=current_user.id)
        elif contest_id:
            queryset = Work.objects.filter(contest_id=contest_id, status=status_param)
        else:
            queryset = Work.objects.filter(status=status_param)

        queryset = queryset.order_by('-created_at')

        try:
            page = int(request.GET.get('page', 1))
            per_page = int(request.GET.get('per_page', 12))
            if page < 1: page = 1
            if per_page < 1: per_page = 12
            if per_page > 100: per_page = 100
        except (ValueError, TypeError):
            page = 1
            per_page = 12

        total = queryset.count()
        total_pages = (total + per_page - 1) // per_page if total > 0 else 1
        if page > total_pages:
            page = total_pages

        start = (page - 1) * per_page
        end = start + per_page
        page_queryset = queryset[start:end]

        data = []
        for w in page_queryset:
            data.append({
                'id': w.id,
                'title': w.title,
                'image': w.image,
                'status': w.status,
                'votes_count': w.votes_count or 0,
                'views': w.views or 0,
                'user_id': w.user_id,
                'contest_id': w.contest_id,
                'created_at': w.created_at.strftime('%Y-%m-%d %H:%M:%S') if w.created_at else ''
            })

        return JsonResponse({
            'code': 200,
            'meta': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': total_pages
            },
            'data': data
        }, safe=False, status=200)
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

    if user.role_id not in (3, 4):
        return JsonResponse({'code': 403, "message": "Недостаточно прав"}, status=403)

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
        author_email = author.email if author else '_'

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
    # ИСПРАВЛЕНО: было request.header.get, стало request.headers.get
    auth_header = request.headers.get('Authorization')

    if auth_header and len(auth_header.split()) == 2:
        token = auth_header.split()[-1]
        user = get_user(token, 'api_access')

    if not user:
        return JsonResponse({'code': 401, 'message': 'Пользователь не авторизован'}, status=401)

    ticket = generate_token(user, salt='ws_ticket')
    if not ticket:
        return JsonResponse({'code': 500, 'error': 'Ошибка, тикет не создан'}, status=500)

    return JsonResponse({'ticket': ticket})


def main(request):
    return JsonResponse({'code': 200, 'message': 'API работает'}, safe=False, status=200)


def test(request):
    return HttpResponse()

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

        # Проверка прав: только organizer (3) или admin (4) могут создавать конкурсы
        if user.role_id not in (3, 4):
            return JsonResponse({'code': 403, 'message': 'Недостаточно прав для создания конкурса'}, status=403)

        title = request.POST.get('title')

        if not title:
            return JsonResponse({'code': 422, 'message': 'Название обязательно'}, status=422)

        contest = Contest.objects.create(
            title=title,
            description=request.POST.get('description', ''),
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

        # пагинация
        try:
            page = int(request.GET.get('page', 1))
            per_page = int(request.GET.get('per_page', 10))
            if page < 1:
                page = 1
            if per_page < 1:
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
                'created_at': c.created_at.strftime('%Y-%m-%d %H:%M:%S') if c.created_at else ''
            })
        return JsonResponse({
            'meta': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': total_pages
            },
            'data': contests_list
        }, safe=False, status=200)

    return JsonResponse({'code': 405, 'message': 'Метод не поддерживается'}, status=405)

def generate_refresh_token(user):
    secret = secrets.token_urlsafe(64)
    user.token = make_password(secret)
    user.save(update_fields=['token'])
    return f'{user.id}:{secret}'  # Исправлено


def verify_refresh_token(raw):
    if not raw or ':' not in raw:
        return None

    id_user, secret = raw.split(':', 1)

    try:
        # ИСПРАВЛЕНО: было pk_user=id_user, стало id=id_user (так как в БД поле называется id)
        user = User.objects.filter(id=id_user).first()
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


@csrf_exempt
def logout_refresh(request):
    """Выход с использованием refresh token"""
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'message': 'Метод не поддерживается'}, status=405)

    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return JsonResponse({'code': 401, 'message': 'Токен не передан'}, status=401)

    parts = auth_header.split()
    if len(parts) != 2 or parts[0] != 'Bearer':
        return JsonResponse({'code': 401, 'message': 'Неверный формат токена'}, status=401)

    user = get_user(parts[1], 'api_access')
    if not user:
        return JsonResponse({'code': 401, 'message': 'Токен недействителен'}, status=401)

    revoke_refresh_token(user)
    return JsonResponse({'code': 200, 'message': 'Вы вышли'}, status=200)
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


@csrf_exempt
def moderate_work(request):
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'message': 'Метод не поддерживается'}, status=405)

    # 1. Проверка авторизации
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return JsonResponse({'code': 401, 'message': 'Токен не передан'}, status=401)

    parts = auth_header.split()
    if len(parts) != 2 or parts[0] != 'Bearer':
        return JsonResponse({'code': 401, 'message': 'Неверный формат токена'}, status=401)

    user = get_user(parts[1], salt='api_access')
    if not user:
        return JsonResponse({'code': 401, 'message': 'Токен недействителен или просрочен'}, status=401)

    # 2. Проверка прав (роль 1 или 3 - админ/жюри)
    if user.role_id not in (3, 4):  # organizer или admin
        return JsonResponse({'code': 403, 'message': 'Недостаточно прав для модерации'}, status=403)

    # 3. Получение данных
    work_id = request.POST.get('work_id')
    action = request.POST.get('action')  # 'approve' или 'reject'

    if not work_id or not action:
        return JsonResponse({'code': 422, 'message': 'Укажите work_id и action'}, status=422)

    if action not in ('approve', 'reject'):
        return JsonResponse({'code': 422, 'message': 'Некорректное действие'}, status=422)

    # 4. Поиск работы
    try:
        work = Work.objects.get(id=int(work_id))
    except Work.DoesNotExist:
        return JsonResponse({'code': 404, 'message': 'Работа не найдена'}, status=404)

    # 5. Обновление статуса
    if action == 'approve':
        work.status = 'approved'
        message = 'Работа одобрена и опубликована'
    else:
        work.status = 'rejected'
        message = 'Работа отклонена'

    work.save(update_fields=['status'])

    return JsonResponse({
        'code': 200,
        'message': message,
        'data': {'work_id': work.id, 'status': work.status}
    }, status=200)
def index(request):
    return render(request, 'index.html')
def login_page(request):
    return render(request, 'login.html')
def contest_page(request):
    return render(request, 'contest.html')
def profile_page(request):
    return render(request, 'profile.html')
def admin_page(request):
    return render(request, 'admin.html')


from django.db import IntegrityError

@csrf_exempt
def votes(request):
    if request.method == 'POST':
        # 1. Проверка авторизации
        auth_header = request.headers.get('Authorization')
        if not auth_header or len(auth_header.split()) != 2 or auth_header.split()[0] != 'Bearer':
            return JsonResponse({'code': 401, 'message': 'Токен не передан или неверен'}, status=401)

        user = get_user(auth_header.split()[1], salt='api_access')
        if not user:
            return JsonResponse({'code': 401, 'message': 'Токен недействителен или просрочен'}, status=401)

        # 2. Получение данных
        work_id = request.POST.get('work_id')
        contest_id = request.POST.get('contest_id')

        if not work_id or not contest_id:
            return JsonResponse({'code': 422, 'message': 'Необходимо указать work_id и contest_id'}, status=422)

        # 3. Валидация существования объектов
        try:
            work = Work.objects.get(id=work_id, contest_id=contest_id, status='approved')
            contest = Contest.objects.get(id=contest_id)
        except (Work.DoesNotExist, Contest.DoesNotExist):
            return JsonResponse({'code': 404, 'message': 'Работа или конкурс не найдены'}, status=404)

        # 4. Проверка статуса конкурса
        if contest.status != 'voting':
            return JsonResponse(
                {'code': 403, 'message': 'Голосование в этом конкурсе еще не началось или уже завершено'}, status=403)

        # 5. Создание голоса и защита от накрутки
        try:
            if Vote.objects.filter(user_id=user.id, contest_id=contest.id).exists():
                return JsonResponse({'code': 409, 'message': 'Вы уже голосовали в этом конкурсе'}, status=409)

            Vote.objects.create(
                user_id=user.id,
                contest_id=contest.id,
                work_id=work.id
            )

            work.votes_count = (work.votes_count or 0) + 1
            work.save(update_fields=['votes_count'])

            return JsonResponse({
                'code': 201,
                'message': 'Голос успешно засчитан',
                'data': {
                    'work_id': work.id,
                    'votes_count': work.votes_count
                }
            }, status=201)

        except IntegrityError:
            return JsonResponse({'code': 409, 'message': 'Вы уже голосовали в этом конкурсе'}, status=409)

    elif request.method == 'GET':
        # Получаем голос текущего пользователя в указанном конкурсе (для фронтенда)
        auth_header = request.headers.get('Authorization')
        if not auth_header or len(auth_header.split()) != 2 or auth_header.split()[0] != 'Bearer':
            return JsonResponse({'code': 401, 'message': 'Токен не передан или неверен'}, status=401)

        user = get_user(auth_header.split()[1], salt='api_access')
        if not user:
            return JsonResponse({'code': 401, 'message': 'Токен недействителен или просрочен'}, status=401)

        contest_id = request.GET.get('contest_id')
        if not contest_id:
            return JsonResponse({'code': 422, 'message': 'Укажите contest_id'}, status=422)

        vote = Vote.objects.filter(user_id=user.id, contest_id=contest_id).first()
        return JsonResponse({
            'code': 200,
            'data': {
                'work_id': vote.work_id if vote else None
            }
        }, status=200)

    return JsonResponse({'code': 405, 'message': 'Метод не поддерживается'}, status=405)


@csrf_exempt
def profile(request):
    """Получение/обновление профиля текущего пользователя"""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return JsonResponse({'code': 401, 'message': 'Токен не передан'}, status=401)
    parts = auth_header.split()
    if len(parts) != 2 or parts[0] != 'Bearer':
        return JsonResponse({'code': 401, 'message': 'Неверный формат токена'}, status=401)
    user = get_user(parts[1], salt='api_access')
    if not user:
        return JsonResponse({'code': 401, 'message': 'Токен недействителен или просрочен'}, status=401)

    if request.method == 'GET':
        return JsonResponse({
            'code': 200,
            'data': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'avatar': user.avatar,
                'role_id': user.role_id,
                'is_active': user.is_active,
                'created_at': user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else ''
            }
        }, status=200)

    elif request.method == 'POST':
        updated_fields = []
        errors = {}

        # --- Обновление username ---
        new_username = request.POST.get('username')
        if new_username:
            if ' ' in new_username or not new_username.isalpha() or not new_username.isascii():
                errors['username'] = ['Имя должно состоять только из латинских букв без пробелов']
            elif User.objects.filter(username=new_username).exclude(id=user.id).exists():
                errors['username'] = ['Логин уже занят']
            else:
                user.username = new_username
                updated_fields.append('username')

        # --- Обновление email ---
        new_email = request.POST.get('email')
        if new_email:
            if '@' not in new_email:
                errors['email'] = ['Введите корректный email']
            elif User.objects.filter(email=new_email).exclude(id=user.id).exists():
                errors['email'] = ['Email уже зарегистрирован']
            else:
                user.email = new_email
                # При смене email деактивируем аккаунт до повторного подтверждения
                user.is_active = False
                updated_fields.extend(['email', 'is_active'])
                # Отправляем новое письмо активации
                activation_token = generate_token(user, 'activation')
                activation_link = request.build_absolute_uri(
                    f"{reverse('email_confirm')}?token={activation_token}"
                )
                send_activation_email(user, activation_link)

        # --- Обновление аватара ---
        avatar = request.FILES.get('avatar')
        if avatar:
            if avatar.size > 5 * 1024 * 1024:
                errors['avatar'] = ['Аватар слишком большой (макс. 5 МБ)']
            elif avatar.content_type not in ['image/jpeg', 'image/png', 'image/webp']:
                errors['avatar'] = ['Только JPEG, PNG или WEBP']
            else:
                ext = avatar.name.split('.')[-1].lower()
                # ИСПРАВЛЕНО: убран дублирующийся префикс "avatars/"
                filename = f"user_{user.id}_{uuid.uuid4()}.{ext}"
                avatars_dir = os.path.join(settings.MEDIA_ROOT, 'avatars')
                os.makedirs(avatars_dir, exist_ok=True)
                filepath = os.path.join(avatars_dir, filename)
                with open(filepath, 'wb+') as f:
                    for chunk in avatar.chunks():
                        f.write(chunk)
                user.avatar = f"avatars/{filename}"
                updated_fields.append('avatar')

        # --- Возврат результата ---
        if errors:
            return JsonResponse({
                'code': 422,
                'message': 'Некорректные данные',
                'errors': errors
            }, status=422)

        if updated_fields:
            user.save(update_fields=updated_fields)

        return JsonResponse({
            'code': 200,
            'message': 'Профиль обновлён',
            'data': {
                'username': user.username,
                'email': user.email,
                'avatar': user.avatar,
                'is_active': user.is_active
            }
        }, status=200)

    return JsonResponse({'code': 405, 'message': 'Метод не поддерживается'}, status=405)


@csrf_exempt
def change_password(request):
    """Смена пароля"""
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'message': 'Метод не поддерживается'}, status=405)

    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return JsonResponse({'code': 401, 'message': 'Токен не передан'}, status=401)

    parts = auth_header.split()
    if len(parts) != 2 or parts[0] != 'Bearer':
        return JsonResponse({'code': 401, 'message': 'Неверный формат токена'}, status=401)

    user = get_user(parts[1], salt='api_access')
    if not user:
        return JsonResponse({'code': 401, 'message': 'Токен недействителен или просрочен'}, status=401)

    old_password = request.POST.get('old_password')
    new_password = request.POST.get('new_password')

    if not old_password or not new_password:
        return JsonResponse({'code': 422, 'message': 'Заполните все поля'}, status=422)

    if not check_password(old_password, user.password):
        return JsonResponse({'code': 401, 'message': 'Неверный текущий пароль'}, status=401)

    if len(new_password) < 8:
        return JsonResponse({'code': 422, 'message': 'Пароль должен содержать минимум 8 символов'}, status=422)

    if not any(c.isdigit() for c in new_password):
        return JsonResponse({'code': 422, 'message': 'Пароль должен содержать хотя бы одну цифру'}, status=422)

    if not any(c in '!@#$%^&*()_+-=' for c in new_password):
        return JsonResponse({'code': 422, 'message': 'Пароль должен содержать спецсимвол'}, status=422)

    user.password = make_password(new_password)
    user.save(update_fields=['password'])

    return JsonResponse({'code': 200, 'message': 'Пароль успешно изменён'}, status=200)


@csrf_exempt
def admin_dashboard(request):
    """Дашборд для администратора"""
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return JsonResponse({'code': 401, 'message': 'Токен не передан'}, status=401)

    parts = auth_header.split()
    if len(parts) != 2 or parts[0] != 'Bearer':
        return JsonResponse({'code': 401, 'message': 'Неверный формат токена'}, status=401)

    user = get_user(parts[1], salt='api_access')
    if not user:
        return JsonResponse({'code': 401, 'message': 'Токен недействителен или просрочен'}, status=401)

    if user.role_id not in (3, 4):
        return JsonResponse({'code': 403, 'message': 'Недостаточно прав'}, status=403)

    if request.method == 'GET':
        # Статистика
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        total_contests = Contest.objects.count()
        total_works = Work.objects.count()
        pending_works = Work.objects.filter(status='pending').count()
        total_votes = Vote.objects.count()

        return JsonResponse({
            'code': 200,
            'data': {
                'total_users': total_users,
                'active_users': active_users,
                'total_contests': total_contests,
                'total_works': total_works,
                'pending_works': pending_works,
                'total_votes': total_votes
            }
        }, status=200)

    return JsonResponse({'code': 405, 'message': 'Метод не поддерживается'}, status=405)


@csrf_exempt
def change_contest_status(request, contest_id):
    """Смена статуса конкурса (только для organizer/admin)"""
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'message': 'Метод не поддерживается'}, status=405)

    # 1. Проверка авторизации
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return JsonResponse({'code': 401, 'message': 'Токен не передан'}, status=401)

    parts = auth_header.split()
    if len(parts) != 2 or parts[0] != 'Bearer':
        return JsonResponse({'code': 401, 'message': 'Неверный формат токена'}, status=401)

    user = get_user(parts[1], salt='api_access')
    if not user:
        return JsonResponse({'code': 401, 'message': 'Токен недействителен или просрочен'}, status=401)

    # 2. Проверка прав
    if user.role_id not in (3, 4):
        return JsonResponse({'code': 403, 'message': 'Недостаточно прав'}, status=403)

    # 3. Поиск конкурса
    try:
        contest = Contest.objects.get(id=int(contest_id))
    except Contest.DoesNotExist:
        return JsonResponse({'code': 404, 'message': 'Конкурс не найден'}, status=404)

    # 4. Получаем желаемый статус
    new_status = request.POST.get('status')
    valid_transitions = {
        'draft': 'open',
        'open': 'voting',
        'voting': 'closed'
    }

    if new_status not in valid_transitions.values():
        return JsonResponse({'code': 422, 'message': 'Некорректный статус'}, status=422)

    # 5. Проверяем, что переход разрешён
    if contest.status not in valid_transitions:
        return JsonResponse({'code': 400, 'message': 'Нельзя изменить статус этого конкурса'}, status=400)

    if valid_transitions[contest.status] != new_status:
        return JsonResponse({'code': 400, 'message': f'Нельзя перейти из {contest.status} в {new_status}'}, status=400)

    # 6. Дополнительные проверки для перехода open -> voting
    if contest.status == 'open' and new_status == 'voting':
        approved_works = Work.objects.filter(contest_id=contest.id, status='approved').count()
        if approved_works == 0:
            return JsonResponse({'code': 400, 'message': 'Нельзя начать голосование: нет одобренных работ'}, status=400)

        # Устанавливаем даты голосования
        contest.voting_start = timezone.now()
        contest.voting_end = timezone.now() + timezone.timedelta(days=7)  # Голосование длится 7 дней

    # 7. Дополнительные действия для перехода voting -> closed
    if contest.status == 'voting' and new_status == 'closed':
        contest.results_date = timezone.now()
        # Здесь можно добавить автоматический подсчёт победителей

    # 8. Устанавливаем даты для перехода draft -> open
    if contest.status == 'draft' and new_status == 'open':
        contest.submission_start = timezone.now()
        contest.submission_end = timezone.now() + timezone.timedelta(days=14)  # Приём работ 14 дней

    # 9. Обновляем статус
    old_status = contest.status  # ← сохраняем ДО изменения
    contest.status = new_status
    contest.updated_at = timezone.now()
    contest.save()
    return JsonResponse({
        'code': 200,
        'message': f'Статус конкурса изменён на {new_status}',
        'data': {
            'contest_id': contest.id,
            'old_status': old_status,
            'new_status': new_status
        }
    }, status=200)


@csrf_exempt
def get_contest_winners(request, contest_id):
    """Получение топ-3 работ конкурса для пьедестала"""
    if request.method != 'GET':
        return JsonResponse({'code': 405, 'message': 'Метод не поддерживается'}, status=405)

    try:
        contest = Contest.objects.get(id=int(contest_id))
    except Contest.DoesNotExist:
        return JsonResponse({'code': 404, 'message': 'Конкурс не найден'}, status=404)

    # Пьедестал показываем только для завершённых конкурсов
    if contest.status != 'closed':
        return JsonResponse({'code': 400, 'message': 'Конкурс ещё не завершён'}, status=400)

    # Берём топ-3 одобренных работы по количеству голосов
    winners = Work.objects.filter(
        contest_id=contest_id,
        status='approved'
    ).order_by('-votes_count')[:3]

    data = []
    for rank, work in enumerate(winners, start=1):
        data.append({
            'rank': rank,
            'id': work.id,
            'title': work.title,
            'image': work.image,
            'votes_count': work.votes_count or 0,
            'user_id': work.user_id
        })

    return JsonResponse({'code': 200, 'data': data}, status=200)

@csrf_exempt
def comments(request):
    """
    Работа с комментариями к фотоработам.
    GET  /api/comments/?work_id=...  — список комментариев
    POST /api/comments/              — создать комментарий
    """
    # ============ GET: список комментариев ============
    if request.method == 'GET':
        work_id = request.GET.get('work_id')
        if not work_id:
            return JsonResponse({'code': 422, 'message': 'Укажите work_id'}, status=422)

        try:
            work = Work.objects.get(id=int(work_id))
        except (Work.DoesNotExist, ValueError, TypeError):
            return JsonResponse({'code': 404, 'message': 'Работа не найдена'}, status=404)

        if work.status != 'approved':
            return JsonResponse({'code': 403, 'message': 'Комментарии недоступны для этой работы'}, status=403)

        try:
            contest = Contest.objects.get(id=work.contest_id)
            if not contest.comments_enabled:
                return JsonResponse({'code': 403, 'message': 'Комментарии отключены для этого конкурса'}, status=403)
        except Contest.DoesNotExist:
            return JsonResponse({'code': 404, 'message': 'Конкурс не найден'}, status=404)

        try:
            page = int(request.GET.get('page', 1))
            per_page = int(request.GET.get('per_page', 20))
            if page < 1: page = 1
            if per_page < 1 or per_page > 100: per_page = 20
        except (ValueError, TypeError):
            page = 1
            per_page = 20

        queryset = Comment.objects.filter(work_id=work.id).select_related('user').order_by('-created_at')
        total = queryset.count()
        total_pages = (total + per_page - 1) // per_page if total > 0 else 1
        if page > total_pages:
            page = total_pages
        start = (page - 1) * per_page
        end = start + per_page

        data = []
        for c in queryset[start:end]:
            data.append({
                'id': c.id,
                'text': c.text,
                'user_id': c.user_id,
                'username': c.user.username if c.user else 'Unknown',
                'avatar': c.user.avatar if c.user else None,
                'created_at': c.created_at.strftime('%Y-%m-%d %H:%M:%S') if c.created_at else '',
                'updated_at': c.updated_at.strftime('%Y-%m-%d %H:%M:%S') if c.updated_at else ''
            })

        return JsonResponse({
            'code': 200,
            'meta': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': total_pages
            },
            'data': data
        }, status=200)

    # ============ POST: создание комментария ============
    elif request.method == 'POST':
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return JsonResponse({'code': 401, 'message': 'Токен не передан'}, status=401)
        parts = auth_header.split()
        if len(parts) != 2 or parts[0] != 'Bearer':
            return JsonResponse({'code': 401, 'message': 'Неверный формат токена'}, status=401)
        user = get_user(parts[1], salt='api_access')
        if not user:
            return JsonResponse({'code': 401, 'message': 'Токен недействителен или просрочен'}, status=401)

        work_id = request.POST.get('work_id')
        text = request.POST.get('text', '').strip()

        if not work_id:
            return JsonResponse({'code': 422, 'message': 'Укажите work_id'}, status=422)
        if not text:
            return JsonResponse({'code': 422, 'message': 'Текст комментария не может быть пустым'}, status=422)
        if len(text) > 5000:
            return JsonResponse({'code': 422, 'message': 'Комментарий слишком длинный (макс. 5000 символов)'}, status=422)

        try:
            work = Work.objects.get(id=int(work_id))
        except (Work.DoesNotExist, ValueError, TypeError):
            return JsonResponse({'code': 404, 'message': 'Работа не найдена'}, status=404)

        if work.status != 'approved':
            return JsonResponse({'code': 403, 'message': 'Комментарии недоступны для этой работы'}, status=403)

        try:
            contest = Contest.objects.get(id=work.contest_id)
            if not contest.comments_enabled:
                return JsonResponse({'code': 403, 'message': 'Комментарии отключены для этого конкурса'}, status=403)
        except Contest.DoesNotExist:
            return JsonResponse({'code': 404, 'message': 'Конкурс не найден'}, status=404)

        # Создаем комментарий (используем comment_obj, чтобы не перекрывать имя функции)
        comment_obj = Comment.objects.create(
            work_id=work.id,
            user_id=user.id,
            text=text
        )

        return JsonResponse({
            'code': 201,
            'message': 'Комментарий добавлен',
            'data': {
                'id': comment_obj.id,
                'text': comment_obj.text,
                'user_id': comment_obj.user_id,
                'username': user.username,
                'avatar': user.avatar,
                'created_at': comment_obj.created_at.strftime('%Y-%m-%d %H:%M:%S') if comment_obj.created_at else ''
            }
        }, status=201)

    return JsonResponse({'code': 405, 'message': 'Метод не поддерживается'}, status=405)


@csrf_exempt
def delete_comment(request, comment_id):
    """Удаление комментария (только автор или модератор/админ)"""
    if request.method != 'DELETE':
        return JsonResponse({'code': 405, 'message': 'Метод не поддерживается'}, status=405)

    # 1. Авторизация
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return JsonResponse({'code': 401, 'message': 'Токен не передан'}, status=401)
    parts = auth_header.split()
    if len(parts) != 2 or parts[0] != 'Bearer':
        return JsonResponse({'code': 401, 'message': 'Неверный формат токена'}, status=401)
    user = get_user(parts[1], salt='api_access')
    if not user:
        return JsonResponse({'code': 401, 'message': 'Токен недействителен или просрочен'}, status=401)

    # 2. Поиск комментария
    try:
        comment = Comment.objects.get(id=int(comment_id))
    except (Comment.DoesNotExist, ValueError, TypeError):
        return JsonResponse({'code': 404, 'message': 'Комментарий не найден'}, status=404)

    # 3. Проверка прав: автор или модератор (role 3/4)
    if comment.user_id != user.id and user.role_id not in (3, 4):
        return JsonResponse({'code': 403, 'message': 'Недостаточно прав для удаления'}, status=403)

    # 4. Удаление
    comment.delete()
    return JsonResponse({'code': 200, 'message': 'Комментарий удалён'}, status=200)


@csrf_exempt
def increment_work_views(request, work_id):
    """Инкремент счётчика просмотров работы"""
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'message': 'Метод не поддерживается'}, status=405)

    try:
        work = Work.objects.get(id=work_id)
    except Work.DoesNotExist:
        return JsonResponse({'code': 404, 'message': 'Работа не найдена'}, status=404)

    # Увеличиваем счётчик
    work.views = (work.views or 0) + 1
    work.save(update_fields=['views'])

    return JsonResponse({
        'code': 200,
        'message': 'Просмотр засчитан',
        'data': {
            'work_id': work.id,
            'views': work.views
        }
    }, status=200)


@csrf_exempt
def block_user(request, user_id):
    """Блокировка/разблокировка пользователя (только для администратора)"""
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'message': 'Метод не поддерживается'}, status=405)

    # 1. Авторизация
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return JsonResponse({'code': 401, 'message': 'Токен не передан'}, status=401)
    parts = auth_header.split()
    if len(parts) != 2 or parts[0] != 'Bearer':
        return JsonResponse({'code': 401, 'message': 'Неверный формат токена'}, status=401)

    admin = get_user(parts[1], salt='api_access')
    if not admin:
        return JsonResponse({'code': 401, 'message': 'Токен недействителен или просрочен'}, status=401)

    # 2. Проверка прав: только администратор (role_id=4)
    if admin.role_id != 4:
        return JsonResponse({'code': 403, 'message': 'Недостаточно прав. Требуется роль администратора'}, status=403)

    # 3. Поиск пользователя
    try:
        target_user = User.objects.get(id=int(user_id))
    except (User.DoesNotExist, ValueError, TypeError):
        return JsonResponse({'code': 404, 'message': 'Пользователь не найден'}, status=404)

    # 4. Нельзя заблокировать самого себя
    if target_user.id == admin.id:
        return JsonResponse({'code': 400, 'message': 'Нельзя заблокировать самого себя'}, status=400)

    # 5. Получаем действие
    action = request.POST.get('action', 'block')
    if action not in ('block', 'unblock'):
        return JsonResponse({'code': 422, 'message': 'Некорректное действие. Используйте block или unblock'},
                            status=422)

    # 6. Выполняем действие
    if action == 'block':
        if not target_user.is_active:
            return JsonResponse({'code': 400, 'message': 'Пользователь уже заблокирован'}, status=400)
        target_user.is_active = False
        target_user.save(update_fields=['is_active'])
        return JsonResponse({
            'code': 200,
            'message': f'Пользователь {target_user.username} заблокирован',
            'data': {'user_id': target_user.id, 'is_active': False}
        }, status=200)
    else:
        if target_user.is_active:
            return JsonResponse({'code': 400, 'message': 'Пользователь уже активен'}, status=400)
        target_user.is_active = True
        target_user.save(update_fields=['is_active'])
        return JsonResponse({
            'code': 200,
            'message': f'Пользователь {target_user.username} разблокирован',
            'data': {'user_id': target_user.id, 'is_active': True}
        }, status=200)