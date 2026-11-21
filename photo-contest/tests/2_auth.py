from pprint import pprint
import requests

url = 'http://localhost:8000/api/auth/'
data = {
    "email": "ilasemonaev32232@gmail.com",
    "password": "Tqwe1!pass",
}

response = requests.post(url, data=data)
print(response.status_code)
pprint(response.json())