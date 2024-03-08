import json
import re
from datetime import datetime
from typing import List
from urllib.parse import urlencode, quote, urlparse, parse_qs

from bs4 import BeautifulSoup

from scraper.strategies.abstract import AbstractCrawler
from scraper.strategies.airbnb_com.downloader import download
from scraper.strategies.airbnb_com.detail_page import AirbnbComDetailStrategy

class AirbnbComSearchStrategy(AbstractCrawler):

    def __init__(self, logger):
        self.origin_url = None
        self.logger=logger

    def execute(self, config) -> List:
        self.origin_url = config.get('url')
        page_limit = config.get('page_limit', None)
        results = self._crawl_listing(self.origin_url,page_limit=page_limit)

        return results
    
    def _crawl_listing(self, url, page_limit=None):
        self.origin_url = url
        next_page_url = url
        results = []
        initial_raw = None
        payload = None
        api_headers = None
        search_operation_id = None
        page = 1
        start_rank = 1
        try:
            while(next_page_url):
                self.logger.info(f'Connecting to: {next_page_url}')
                raw_data = download(next_page_url, headers=api_headers, data=payload)
                if not raw_data:
                    self.logger.info(f"No raw data found")
                    break
                
                if initial_raw is None:
                    initial_raw = raw_data

                self.logger.info(f'Parsing Data')
                result = self.parse(raw_data, start_rank)
                if not result:
                    break
                results.append(result)
    
                if search_operation_id is None:
                    search_operation_id = self.fetch_search_operation_id(raw_data)

                payload = self.generate_search_api_payload(initial_raw, page, search_operation_id)
                if not payload:
                    break

                if api_headers is None:
                    soup = BeautifulSoup(raw_data, 'lxml')
                    api_headers = self.generate_api_headers(soup, url)
                next_page_url = self.generate_search_api_url(search_operation_id)

                if page_limit and page_limit >= page:
                    break
                page += 1
                start_rank = len(result) + start_rank

        except Exception as e:
            self.logger.info(str(e))
        return results
    
    def get_next_page(self, raw_data, url):
        next_url = None
        soup = BeautifulSoup(raw_data, 'lxml')
        deffered_state_json = self.get_deffered_state(soup)
        pagination_json =  self.get_pagination_json(deffered_state_json)
        if pagination_json:
            next_page_cursor = pagination_json.get('page_info', {}).get('nextPageCursor')
            session_id = pagination_json.get('session_id')
            if next_page_cursor and session_id:
                next_url = f'{url}&federated_search_session_id={session_id}&pagination_search=true&cursor={quote(next_page_cursor)}'
        return next_url

    
    def parse(self, raw_data, start_rank):
        results = []
        listing_items_json = []
        if '<!doctype html' in raw_data:
            soup = BeautifulSoup(raw_data, 'lxml')
            deffered_state_json = self.get_deffered_state(soup)
            listing_items_json = self.get_listing_items(deffered_state_json)
        else:
            state_json = json.loads(raw_data)
            listing_items_json = self.get_listing_items(state_json)

        try:
            dates = self.get_check_dates()
            check_in = dates.get('checkin')
            check_out = dates.get('checkout')
            rank = start_rank
            for item in listing_items_json:
                url = self.get_url(item)
                room_data = {}
                if item.get('__typename') == 'SkinnyListingItem':
                    config = {"with_price": True}
                    room_data = self.fetch_room_data(url, config)
                    title = room_data.get('title')
                    image_url = room_data.get('image_url')
                    description = room_data.get('description')
                    price_per_night = room_data.get('price_per_night')
                    orig_price_per_night = room_data.get('orig_price_per_night')
                    total_price = room_data.get('total_price')
                    rating_score = room_data.get('rating_score')
                    rating_count = room_data.get('rating_count')
                else:
                    room_data = self.fetch_room_data(url)
                title = self.get_title(item)
                description = self.get_description(item)
                price_per_night = self.get_price_per_night(item)
                orig_price_per_night = self.get_orig_price_per_night(item)
                total_price = self.get_total_price(item)
                rating_score = self.get_rating_score(item)
                rating_count = self.get_rating_count(item)
                labels = self.get_labels(item)
                image_url = self.get_image_url(item)
                # guests = self.get_pdp_guests(room_data)

                data = {
                    "check_in_date": check_in,
                    "check_out_date": check_out,
                    "rank": rank,
                    "label": title,
                    "url": url,
                    "description": description,
                    "currency": "USD",
                    "price_per_night": price_per_night,
                    "orig_price_per_night": orig_price_per_night,
                    "total_price": total_price,
                    "rating_score": rating_score,
                    "rating_count": rating_count,
                    "labels": labels,
                    "image_url": image_url,

                }
                data.update(room_data)
                rank += 1
                results.append(data)
        except Exception as e:
            self.logger.info(str(e))
        return results
    
    def get_url(self, item_json):
        value = str()
        try:
            quary_params = {}
            parsed = urlparse(self.origin_url)
            parsed_query = parse_qs(parsed.query)
            adults = parsed_query.get('adults')
            if adults:
                quary_params.update({'adults': adults[0]})
            check_in = parsed_query.get('checkin')
            if check_in:
                quary_params.update({'check_in': check_in[0]})
            check_out = parsed_query.get('checkout')
            if check_out:
                quary_params.update({'check_out': check_out[0]})

            base_url = 'https://www.airbnb.com/rooms/'
            id = item_json.get('listing', {}).get('id') \
                or item_json.get('listingId')
            if id and quary_params:
                value = f'{base_url}{id.strip()}?{urlencode(quary_params, quote_via=quote)}'
            elif id:
                value = f'{base_url}{id.strip()}'
        except Exception as e:
            self.logger.info(str(e))
        return value

    def get_pagination_json(self, deffered_state_json):
        client_data = deffered_state_json.get('niobeMinimalClientData')
        try:
            pagination = {}
            if client_data:
                search_result = client_data[0][1]
                if search_result:
                    stay_search = search_result.get('data', {}).get('presentation', {}).get('staysSearch')
                    if stay_search:
                        pagination_info = stay_search.get('results', {}).get('paginationInfo')
                        if pagination_info:
                            pagination.update({"page_info": pagination_info})
                        session_id = stay_search.get('results', {}).get('loggingMetadata', {}).get('legacyLoggingContext', {}).get('federatedSearchSessionId')
                        if session_id:
                            pagination.update({"session_id":session_id })

            if pagination:
                return pagination

        except Exception as e:
            self.logger.info(str(e))

        return {}
    
    def generate_search_api_payload(self, raw_data, page, operation_id):
        soup = BeautifulSoup(raw_data, 'lxml')
        
        try:
            deffered_state_json = self.get_deffered_state(soup)
            listing_items_json = self.get_listing_items(deffered_state_json)
            item_ids = [item.get('listing', {}).get('id') for item in listing_items_json]
            pagination_json =  self.get_pagination_json(deffered_state_json)

            client_data = deffered_state_json.get('niobeMinimalClientData')
            search_result = client_data[0][1]
            # the next page cursor is the page number since the cursor index starts at 0
            # but the page start at 1
            cursor = pagination_json.get('page_info', {}).get('pageCursors')[page]
            variables = search_result.get('variables', {})

            variables['staysSearchRequest'].update({
                "cursor": cursor,
                "skipHydrationListingIds": item_ids
                })
            
            variables['staysMapSearchRequestV2'].update({
                "cursor": cursor,
                "skipHydrationListingIds": item_ids
                })
            
            payload = {
                "operationName": "StaysSearch",
                "variables": variables,
                "extensions": {
                    "persistedQuery": {
                    "version": 1,
                    "sha256Hash": operation_id
                    }
                }
            }
            return json.dumps(payload, separators=(',',':'))
        except Exception as e:
            self.logger.info(str(e))

        return None
    
    def fetch_search_operation_id(self, raw_data):
        try:
            soup = BeautifulSoup(raw_data, 'lxml')
            js_url = self.get_search_js_link(soup)
            raw = download(js_url)
            if raw:
                matches = re.search(r"'StaysSearch',type:'query',operationId:'([0-9a-zA-Z]+)'", raw)
                if matches:
                    return matches.group(1)
        except Exception as e:
            self.logger.info(str(e))
        return None

    def generate_search_api_url(self, operation_id):
        return f'https://www.airbnb.com/api/v3/StaysSearch/{operation_id}?operationName=StaysSearch&locale=en&currency=USD'
    
    def get_search_js_link(self, soup):
        ''' This script url will contain the hash of the operation_id for the search api route
        '''
        tag = soup.find('script', src=re.compile('web/common/frontend/stays-search/routes/StaysSearchRoute/StaysSearchRoute.prepare', re.IGNORECASE))
        if tag:
            return tag.get('src')
        return None
    
    def get_injector_instance_json(self, soup):
        try:
            tag = soup.select_one('#data-injector-instances')
            if tag:
                txt = tag.get_text().strip()
                return json.loads(txt)
        except Exception as e:
            self.logger.info(str(e))
        return {}
        
    def generate_api_headers(self, soup, url):
        header = {}
        try:
            injector_json = self.get_injector_instance_json(soup)
            spa_data = injector_json.get('root > core-guest-spa', {})
            bootstrap_token_data= spa_data[0][1]
            api_key = bootstrap_token_data.get('layout-init', {}).get('api_config', {}).get('key')
            header = {
                "authority":"www.airbnb.com",
                "accept":"*/*",
                "accept-language":"en-US,en;q=0.9",
                "content-type":"application/json",
                "referer": url,
                "sec-fetch-dest":"empty",
                "sec-fetch-mode":"cors",
                "sec-fetch-site":"same-origin",
                "user-agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                "x-airbnb-api-key":api_key,
                "x-airbnb-graphql-platform":"web",
                "x-airbnb-graphql-platform-client":"minimalist-niobe",
                "x-airbnb-supports-airlock-v2":"true",
                "x-csrf-token":"null",
                "x-csrf-without-token":"1",
                "x-niobe-short-circuited":"true"
            }
        except Exception as e:
            print('failed to generate api headers')
        return header

    def fetch_room_data(self, url, config={}):

        try:
            strategy = AirbnbComDetailStrategy(self.logger)
            config.update({"url":url})
            room_data = strategy.execute(config)
            if room_data:
                return room_data

        except Exception as e:
            self.logger.info(f'[*] Failed to fetch {str(e)}')
        return {}


    def get_title(self, item_json):
        value = str()
        try:
            txt = item_json.get('listing', {}).get('title')
            if txt:
                return txt.strip()
        except Exception as e:
            self.logger.info(str(e))
        return value

    def get_description(self, item_json):
        value = str()
        try:
            txt = item_json.get('listing', {}).get('name')
            if txt:
                return txt.strip()
        except Exception as e:
            self.logger.info(str(e))
        return value

    def get_price_per_night(self, item_json):
        value = float()
        try:
            price_displays = item_json.get('pricingQuote', {}).get('structuredStayDisplayPrice')
            if price_displays:
                price_txt = price_displays.get('primaryLine', {}).get('price','')
                if not price_txt:
                    price_txt = price_displays.get('primaryLine', {}).get('discountedPrice')
                if price_txt:
                    value = float(re.sub('[^0-9.]', '', price_txt))
        except Exception as e:
            self.logger.info(str(e))
        return value
    
    def get_orig_price_per_night(self, item_json):
        value = float()
        try:
            price_displays = item_json.get('pricingQuote', {}).get('structuredStayDisplayPrice')
            if price_displays:
                price_txt = price_displays.get('primaryLine', {}).get('originalPrice')
                if price_txt:
                    value = float(re.sub('[^0-9.]', '', price_txt))
        except Exception as e:
            self.logger.info(str(e))
        return value


    def get_total_price(self, item_json):
        value = float()
        try:
            price_displays = item_json.get('pricingQuote', {}).get('structuredStayDisplayPrice')
            if price_displays:
                price_txt = price_displays.get('secondaryLine', {}).get('price')
                if price_txt:
                    value = float(re.sub('[^0-9.]', '', price_txt))

        except Exception as e:
            self.logger.info(str(e))
        return value

    def get_rating_score(self, item_json):
        value = float()
        try:
            label_txt = item_json.get('listing', {}).get('avgRatingA11yLabel')
            matches = re.search(r'([0-9.]+) out', label_txt)
            if matches:
                return float(matches.group(1))
        except Exception as e:
            self.logger.info(str(e))
        return value

    def get_rating_count(self, item_json):
        value = int()
        try:
            label_txt = item_json.get('listing', {}).get('avgRatingA11yLabel')
            matches = re.search(r'(\d+) reviews', label_txt)
            if matches:
                return int(matches.group(1))
        except Exception as e:
            self.logger.info(str(e))
        return value


    def get_image_url(self, item_json):
        value = str()
        try:
            images = item_json.get('listing', {}).get('contextualPictures',[])
            if images:
                url = images[0].get('picture')
                if url:
                    return url
        except Exception as e:
            self.logger.info(str(e))
        return value

    def get_labels(self, item_json):
        value = []
        try:
            badges = item_json.get('listing', {}).get('formattedBadges',[])
            if badges:
                for badge in badges:
                    txt = badge.get('text')
                    if txt:
                        value.append(txt.strip())
        except Exception as e:
            self.logger.info(str(e))
        return value
    
    def get_deffered_state(self, soup):
        tag = soup.select_one('script[id^="data-deferred-state"]')
        try:
            if tag:
                txt = tag.get_text().strip()
                return json.loads(txt)
        except Exception as e:
            self.logger.info(str(e))
        return {}

    def get_listing_items(self, state_json):
        client_data = state_json.get('niobeMinimalClientData')
        try:
            if client_data:
                search_result = client_data[0][1]
                if search_result:
                    presentation = search_result.get('data', {}).get('presentation', {})
                    if presentation:
                        return presentation.get('staysSearch', {}).get('results', {}).get('searchResults', [])
            else:
                presentation = state_json.get('data', {}).get('presentation', {})
                if presentation:
                    return presentation.get('staysSearch', {}).get('results', {}).get('searchResults', []) 
        except Exception as e:
            self.logger.info(str(e))
        return []
    
    def get_check_dates(self):
        value = {}
        try:
            parsed = urlparse(self.origin_url)
            parsed_query = parse_qs(parsed.query)
            check_in = parsed_query.get('checkin')
            if check_in:
                value.update({'checkin': check_in[0]})
            check_out = parsed_query.get('checkout')
            if check_out:
                 value.update({'checkout': check_out[0]})
        except Exception as e:
            self.logger.info(str(e))
        return value
    