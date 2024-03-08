from scraper.utils.http_curl import HTTP


def download(url, headers={}, data=None):

    if not headers:
        headers = {
            'authority': 'www.airbnb.com',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'max-age=0',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'viewport-width': '1920',
        }
    http = HTTP()
    if not data:
    
        response = http.get(url, headers=headers )
        if response and response.status_code in [200, 201]:
            return response.text
        else:
            print(response.status_code)
    else:
        response = http.post(url, headers=headers, data=data )
        if response and response.status_code in [200, 201]:
            return response.text
        else:
            print(response.status_code)
    return None

