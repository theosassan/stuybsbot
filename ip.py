import requests
import os
def ip():
  proxies = {
  "http": os.environ['QUOTAGUARDSTATIC_URL'],
  "https": os.environ['QUOTAGUARDSTATIC_URL']
  }

  res = requests.get("http://ip.quotaguard.com/", proxies=proxies)
