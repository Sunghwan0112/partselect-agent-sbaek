import requests

payload = { 'api_key': '294bc68b68df9e77e055922f37a0cb68', 'url': 'https://www.partselect.com/Models/WDT780SAEM1/Parts/?SearchTerm=PS3406971' }
r = requests.get('https://api.scraperapi.com/', params=payload)
print(r.text)
