import urllib.request as req
import urllib.error as err
try:
    print(req.urlopen("http://localhost:8000/api/alerts/summary").read().decode())
except err.HTTPError as e:
    print(e.read().decode())
