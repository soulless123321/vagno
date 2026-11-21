from pprint import pprint
import requests

login_url = 'http://localhost:8000/api/auth/'
login_data = {
    "email": "golub3@yandex.ru",
    "password": "g0lub3@yandex.ru"
}
login_response = requests.post(login_url, data=login_data)
print("Логин", login_response.status_code)
pprint(login_response.json())

token = login_response.json()['data']['token']

url = 'http://localhost:8000/api/contests/'
headers = {'Authorization': f'Bearer {token}'}
data = {
    "title": "Мой первый конкурс",
    "description": "Проверка создания конкурса"
}
response = requests.post(url, headers=headers, data=data)
print("Создание:", response.status_code)
pprint(response.json())