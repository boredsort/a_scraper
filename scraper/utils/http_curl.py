import requests
import os
from dotenv import load_dotenv, find_dotenv
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from curl_cffi import requests as c_requests
load_dotenv(find_dotenv())

class HTTP:
	def __init__(self):
		
		self.session = c_requests.Session()
		self.session.verify = False
		self.session.trust_env = False
		self.session.headers.update({
			    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
		})
		# self.proxy = {
		# 	'http': os.getenv('PROXY_HTTP'),
		# 	'https': os.getenv('PROXY_HTTPS')
		# }
		self.max_retries = 5


	def _send_request(self, method, url, **kwargs):
		# if 'proxies' not in kwargs:
		# 	kwargs.update({
		# 		'proxies': self.proxy
		# 	})
		kwargs.update({'impersonate': "chrome110"})
		error = None
		for _ in range(self.max_retries):
			try:
				response = method(url, **kwargs)
				if response.status_code in [403, 401]:
					raise requests.exceptions.ReadTimeout
				if response.status_code not in [200, 201]:
					raise Exception(f'Status {response.status_code}')
				return response
			
			except requests.exceptions.ReadTimeout:
				self.rotate_proxy()
		
			except Exception as e:
				error = str(e)
				print(f'An error occurred: {error}')
		# raise Exception(error)
	
	def get(self, url, **kwargs):
		return self._send_request(self.session.get, url, **kwargs)
	
	def post(self, url, **kwargs):
		return self._send_request(self.session.post, url, **kwargs)
	
	def head(self, url, **kwargs):
		return self._send_request(self.session.head, url, **kwargs)
	
	def rotate_proxy(self):
		print('Rotating proxy')
		self.session.close()
		# self.proxy = {
		# 	'http': os.getenv('PROXY_HTTP2'),
		# 	'https': os.getenv('PROXY_HTTPS2')
		# }
		self.session = c_requests.Session()
