import requests

login_url = 'http://127.0.0.1:8000/api/auth/'
login_data = {
    "email": "golub3@yandex.ru",
    "password": "g0lub3@yandex.ru",
}
login_response = requests.post(login_url, data=login_data)
print("Логин:", login_response.status_code)
token = login_response.json()['data']['token']

url = 'http://127.0.0.1:8000/api/contests/analytics/'
headers = {'Authorization': f'Bearer {token}'}

response = requests.get(url, headers=headers)
print("Аналитика", response.status_code)

with open('analytics.csv', 'wb') as f:
    f.write(response.content)

print("файл analytics.csv сохранен")