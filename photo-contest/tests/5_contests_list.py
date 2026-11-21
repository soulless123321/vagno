from http.client import responses
from pprint import pprint
import requests

url = 'http://localhoste:8000/api/contests/'
response = requests.get(url)
print("GET all:", response.status_code)
pprint(response.json())

url = 'http://localhoste:8000/api/contests/?filter=open'
response = requests.get(url)
print("\nGET open:", response.status_code)
pprint(response.json())

url = 'http://localhost:8000/api/contests/?sory=title&page=1&per_page=5'
response = requests.get(url)
print("\nGET sorted:", response.status_code)
pprint(response.json())