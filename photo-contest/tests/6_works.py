from pprint import pprint
import requests
from django.contrib.auth.decorators import login_required

login_url = 'http://127.0.0.1:8000/api/auth/'
login_data = {
    "email": "golub3@yandex.ru",
    "password": "g0lub3@yandex.ru",
}
login_response = requests.post(login_url, data=login_data)
print("Логин:", login_response.status_code)
token = login_response.json()['data']['token']

url = 'http://127.0.0.1:8000/api/works/'
headers = {'Authorization': f'Bearer {token}'}

with open('test_image.jpg', 'rb') as f:
    files = {'image': ('photo.jpg', f, 'image/jpeg')}
    data = {
        'contest_id': 1,
        'title': 'Моя работа',
    }
    response = requests.post(url, headers=headers, data=data, files=files)

print("Загрузка:", response.status_code)
print(response.json)