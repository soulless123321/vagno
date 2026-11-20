from pprint import pprint
import requests

url = 'http://localhost:8000/api/users/'
data = {
    "name": "contestuser",
    "email": "contestuser@yandex.ru",
    "password": "Contest1!pass",
}
response = requests.post(url, data=data)
print(response.status_code)
pprint(response.json())