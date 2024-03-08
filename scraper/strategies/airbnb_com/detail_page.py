import json
import re
from datetime import datetime
from typing import Dict
from urllib.parse import urlencode, quote, urlparse, parse_qs

from bs4 import BeautifulSoup

from scraper.strategies.abstract import AbstractCrawler
from scraper.strategies.airbnb_com.downloader import download


class AirbnbComDetailStrategy(AbstractCrawler):

    def __init__(self, logger):
        self.origin_url = None
        self.logger = logger
        self.pdp_operation_id = None
        self.product_id = None

    def execute(self, config) -> Dict:
        self.origin_url = config.get('url')
        url = self.origin_url
        with_pricing_data = config.get('with_price')
        data = {}
        try:
            soup = self.fetch_pdp_soup(url)
            basic_details = self.fetch_basic(url, soup)
            if basic_details:
                data.update(basic_details)

            if with_pricing_data:
                price_details = self.fetch_pdp_price_data(url, soup)
                data.update(price_details)
        except Exception as e:
            self.logger.info(f'[*] Execution Failed {str(e)}')
        return data
    
    def fetch_basic(self, url, soup):
        data = {}
        try:
            initial_room_data = self.fetch_room_data(url, soup, initial=True)
            room_data = self.fetch_room_data(url, soup)
            self.product_id = self.get_pdp_product_id(initial_room_data)
            host_name = self.get_pdp_host_name(room_data)
            cleanliness = self.get_pdp_clean(room_data)
            accuracy = self.get_pdp_clean(room_data)
            communication = self.get_pdp_communication(room_data)
            location_rate = self.get_pdp_location_rating(room_data)
            check_in_rate = self.get_pdp_check_in(room_data)
            guest_capacity = self.get_pdp_capacity(room_data)
            lat = self.get_pdp_lat(initial_room_data)
            lon = self.get_pdp_lon(initial_room_data)
            rooms = self.get_pdp_rooms(room_data)
            amenties = self.get_pdp_amenties(initial_room_data)
            property_type = self.get_property_type(room_data)
            fees = self.get_pdp_fees(room_data)
            title = self.get_pdp_title(room_data)
            description = self.get_pdp_description(room_data)
            image_url = self.get_pdp_image_url(room_data)
            rating_score = self.get_pdp_rating_score(room_data)
            rating_count = self.get_pdp_rating_count(room_data)
            data = {
                "label": title,
                "description": description,
                "image_url": image_url,
                "rating_score": rating_score,
                "rating_count": rating_count,
                "property_type": property_type,
                "host_name": host_name,
                "cleanliness" : cleanliness,
                "accuracy": accuracy,
                "location_rate": location_rate,
                "communication": communication,
                "check_in_rating": check_in_rate,
                "guest": guest_capacity,
                "baths": rooms.get('bath'),
                'beds': rooms.get('beds'),
                'bedrooms': rooms.get('bedroom'),
                'kitchen': amenties.get('kitchen'),
                'pool': amenties.get('pool'),
                'lattitude': lat,
                'longtitude': lon,
                'amenities': amenties.get('extra',[]),
                "cleaning_fee": fees.get('cleaning_fee'),
                "service_fee": fees.get('service_fee'),
            }

        except Exception as e:
            self.logger.info(str(e))
        return data
    

    def fetch_room_data(self, url, soup, initial=False):

        try:
            if initial:
                self.logger.info(f'[*] Fetching initial PDP data {url}')
            else:
                self.logger.info(f'[*] Fetching hidden PDP data {url}')

            pdp_link = self.get_pdp_js_link(soup)
            if pdp_link:

                operation_id = None
                if self.pdp_operation_id is None:
                    operation_id = self.fetch_pdp_operation_id(pdp_link)
                else:
                    operation_id = self.pdp_operation_id

                if operation_id:
                    pdp_api_url = self.generate_pdp_api_url(soup, operation_id, initial=initial)
                    pdp_api_header = self.generate_pdp_api_headers(soup, url)
                    pdp_raw = download(pdp_api_url, headers=pdp_api_header)
                    if pdp_raw:
                        pdp_json = json.loads(pdp_raw)
                        room_data = pdp_json.get('data', {}).get('presentation', {}).get('stayProductDetailPage', {})
                        if room_data:
                            return room_data

        except Exception as e:
            self.logger.info(f'[*] Failed to fetch {str(e)}')
        return {}
    
    def fetch_pdp_soup(self, url):
        try:
            raw = download(url)
            if raw:
                return BeautifulSoup(raw, 'lxml')
        except Exception as e:
            self.logger.info(str(e))
        return None
    
    def get_pdp_js_link(self, soup):
        ''' This script url will contain the hash of the operation_id for the PDP api route
        '''
        tag = soup.find('script', src=re.compile('web/common/frontend/gp-stays-pdp-route/routes/PdpPlatformRoute.prepare', re.IGNORECASE))
        if tag:
            return tag.get('src')
        return None
    
    def get_pdp_js_link_price_prerequisite(self, soup):

        tag = soup.find('script', src=re.compile('web/en/frontend/airmetro/src/browser/asyncRequire'))
        if tag:
            return tag.get('src')
        return None

    def generate_pdp_api_url(self, soup, operation_id, initial=False):
        injector_json = self.get_injector_instance_json(soup)
        spa_data = injector_json.get('root > core-guest-spa', {})
        try:
            if spa_data:
                client_data = spa_data[1][1]
                niobe_data = client_data.get('niobeMinimalClientData',[None])[0][0]

                variables_txt = niobe_data.replace('StaysPdpSections:','')
                variables_json = json.loads(variables_txt)

                if not initial:
                    section_ids = [
                        "CANCELLATION_POLICY_PICKER_MODAL",
                        "BOOK_IT_CALENDAR_SHEET",
                        "POLICIES_DEFAULT",
                        "BOOK_IT_SIDEBAR",
                        "URGENCY_COMMITMENT_SIDEBAR",
                        "BOOK_IT_NAV",
                        "BOOK_IT_FLOATING_FOOTER",
                        "EDUCATION_FOOTER_BANNER",
                        "URGENCY_COMMITMENT",
                        "EDUCATION_FOOTER_BANNER_MODAL"
                    ]
                    variables_json['pdpSectionsRequest'].update({'sectionIds': section_ids})
                
                extensions = json.dumps({"persistedQuery":{"version":1,"sha256Hash":operation_id}},separators=(',',':'))
                query_params = {
                    "operationName": "StaysPdpSections",
                    "locale": "en",
                    "currency": "USD",
                    "variables": json.dumps(variables_json,separators=(',',':')),
                    "extensions": extensions
                }
                return f'https://www.airbnb.com/api/v3/StaysPdpSections/{operation_id}?{urlencode(query_params, quote_via=quote)}'
        except Exception as e:
            self.logger.info(str(e))

        return None
    
    def generate_pdp_checkout_api_url(self, soup):

        checkout_operation_id = self.fetch_checkout_operation_id(soup)

        parsed = urlparse(self.origin_url)
        parsed_query = parse_qs(parsed.query)
        checkin_date = parsed_query.get('check_in')[0]
        checkout_date = parsed_query.get('check_out')[0]
        adults = parsed_query.get('adults',[10])[0]
        children = parsed_query.get('children', [0])[0]
        infant = parsed_query.get('children', [0])[0]

    
        variables_json = {
            "input":{
                "businessTravel":{
                    "workTrip":False
                },
                "checkinDate":checkin_date,
                "checkoutDate":checkout_date,
                "guestCounts":{
                    "numberOfAdults":int(adults),
                    "numberOfChildren":int(children),
                    "numberOfInfants":int(infant),
                    "numberOfPets":0
                },
                "guestCurrencyOverride":"USD",
                "listingDetail":{},"lux":{},
                "metadata":{
                    "internalFlags":["LAUNCH_LOGIN_PHONE_AUTH","LAUNCH_WEB_SBUI_MIGRATION_V2","LAUNCH_WEB_SBUI_MIGRATION_V3"]
                },"org":{},
                "productId":self.product_id,
                "addOn":{"carbonOffsetParams":{"isSelected":False}},
                "quickPayData":None
            },
            "isLeanFragment":False
        }
    
        query_params = {
            "operationName": "stayCheckout",
            "locale": "en",
            "currency": "USD",
            "variables": json.dumps(variables_json,separators=(',',':')),
            "extensions": json.dumps({"persistedQuery":{"version":1,"sha256Hash":checkout_operation_id}},separators=(',',':'))
        }

        return f'https://www.airbnb.com/api/v3/stayCheckout/{checkout_operation_id}?{urlencode(query_params, quote_via=quote)}'

    def generate_pdp_api_headers(self, soup, pdp_url):
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
                "referer": pdp_url,
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
    

    def fetch_checkout_operation_id(self, soup):

        js_link = self.get_pdp_js_link_price_prerequisite(soup)
        try:
            if js_link:
                raw = download(js_link)
                if raw:
                    matches = re.search(r'common\/frontend\/gp-stays-checkout-route\/routes\/StaysCheckoutRoute\/StaysCheckoutCreateRoute.[\d|\w]+.js', raw)
                    if matches:
                        path = matches.group(0)
                        url = f'https://a0.muscache.com/airbnb/static/packages/web/{path}'
                        requirements_raw = download(url)
                        if requirements_raw:
                            matches = re.search(r"'stayCheckout',type:'query',operationId:'([0-9a-zA-Z]+)'", requirements_raw)
                            if matches:
                                return matches.group(1)
                            
        except Exception as e:
            self.logger.info(str(e))
        return str()

        
    def fetch_pdp_operation_id(self, url):
        try:
            raw = download(url)
            if raw:
                matches = re.search(r"'StaysPdpSections',type:'query',operationId:'([0-9a-zA-Z]+)'", raw)
                if matches:
                    return matches.group(1)
        except Exception as e:
            self.logger.info(str(e))
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

    def get_pdp_host_name(self, room_data):
        value = str()
        try:
            sbui_data = room_data.get('sections', {}).get('sbuiData')
            if sbui_data:
                sections = sbui_data.get('sectionConfiguration', {}).get('root', {}).get('sections',[])
                for section in sections:
                    if section.get('sectionId') == 'HOST_OVERVIEW_DEFAULT':
                        sec_data = section.get('sectionData')
                        title = sec_data.get('title')
                        if title:
                            value = title.replace('Hosted by','').strip()
        except Exception as e:
            self.logger.info(str(e))
        return value


    def get_pdp_title(self, room_data):
        meta_data = room_data.get('sections', {}).get('metadata')
        try:
            if meta_data:
                title = meta_data.get('sharingConfig', {}).get('title')
                if title:
                    # Note this is not accurate but this it to fix a listing title bug
                    return title.split('·')[0].strip()
        except Exception as e:
            self.logger.info(str(e))
        return str()
    

    def get_pdp_description(self, room_data):
        meta_data = room_data.get('sections', {}).get('metadata')
        try:
            if meta_data:
                description = meta_data.get('seoFeatures', {}).get('ogTags', {}).get('ogDescription')
                if description:
                    return description.strip()
        except Exception as e:
            self.logger.info(str(e))
        return str()

    def get_pdp_orig_price_per_night(self, room_data):

        pass

    def get_pdp_total_price(self, price_data_json):
        value = float()
        try:
            quick_pay_data = price_data_json.get('sections', {}).get('temporaryQuickPayData', {})
            price_breakdown = quick_pay_data.get('bootstrapPayments', {}).get('productPriceBreakdown', {}).get('priceBreakdown')
            price_items = price_breakdown.get('priceItems')
            if price_items:
                price_data = price_items[0]
                if price_data:
                    total = price_data.get('total')
                    if total:
                        txt = total.get('amountFormatted')
                        value = float(float(re.sub('[^0-9.]', '', txt)))

        except Exception as e:
            self.logger.info(str(e))

        return value
    

    def get_pdp_price_per_night(self, price_data_json):
        value = float()
        try:
            quick_pay_data = price_data_json.get('sections', {}).get('temporaryQuickPayData', {})
            price_breakdown = quick_pay_data.get('bootstrapPayments', {}).get('productPriceBreakdown', {}).get('priceBreakdown')
            price_items = price_breakdown.get('priceItems')
            if price_items:
                price_data = price_items[0]
                if price_data:
                    txt = price_data.get('localizedTitle')
                    if txt:
                        clean_txt = txt.split('x')[0].replace('$','').strip()
                        value = float(clean_txt)

        except Exception as e:
            self.logger.info(str(e))

        return value
    
    def get_pdp_rating_score(self, room_data):
        value = float()
        try:
            meta_data = room_data.get('sections', {}).get('metadata')
            if meta_data:
                rating = meta_data.get('sharingConfig', {}).get('starRating')
                if rating:
                    value = float(rating)
                    
        except Exception as e:
            self.logger.info(str(e))

        return value


    def get_pdp_rating_count(self, room_data):
        value = int()
        try:
            meta_data = room_data.get('sections', {}).get('metadata')
            if meta_data:
                count = meta_data.get('sharingConfig', {}).get('reviewCount')
                if count:
                    value = int(count)
                    
        except Exception as e:
            self.logger.info(str(e))
        return value


    def get_pdp_labels(self, room_data):
        pass

    def get_pdp_image_url(self, room_data):
        value = str()
        try:
            meta_data = room_data.get('sections', {}).get('metadata')
            if meta_data:
                url = meta_data.get('sharingConfig', {}).get('imageUrl')
                if url:
                    value = url
                    
        except Exception as e:
            self.logger.info(str(e))
        return value


    def get_pdp_clean(self, room_data):
        value = float()
        try:
            meta_data = room_data.get('sections', {}).get('metadata')
            if meta_data:
                event_data = meta_data.get('loggingContext', {}).get('eventDataLogging')
                rate = event_data.get('cleanlinessRating', 0)
                if rate:
                    value = rate
        except Exception as e:
            self.logger.info(str(e))
        return value
    

    def get_pdp_communication(self, room_data):
        value = float()
        try:
            meta_data = room_data.get('sections', {}).get('metadata')
            if meta_data:
                event_data = meta_data.get('loggingContext', {}).get('eventDataLogging')
                rate = event_data.get('communicationRating', 0)
                if rate:
                    value = rate
        except Exception as e:
            self.logger.info(str(e))
        return value
    

    def get_pdp_location_rating(self, room_data):
        value = float()
        try:
            meta_data = room_data.get('sections', {}).get('metadata')
            if meta_data:
                event_data = meta_data.get('loggingContext', {}).get('eventDataLogging')
                rate = event_data.get('locationRating', 0)
                if rate:
                    value = rate
        except Exception as e:
            self.logger.info(str(e))
        return value
    

    def get_pdp_check_in(self, room_data):
        value = float()
        try:
            meta_data = room_data.get('sections', {}).get('metadata')
            if meta_data:
                event_data = meta_data.get('loggingContext', {}).get('eventDataLogging')
                rate = event_data.get('checkinRating', 0)
                if rate:
                    value = rate
        except Exception as e:
            self.logger.info(str(e))
        return value
    

    def get_pdp_lat(self, room_data):
        value = str()
        try:
            meta_data = room_data.get('sections', {}).get('metadata')
            if meta_data:
                event_data = meta_data.get('loggingContext', {}).get('eventDataLogging')
                lat = event_data.get('listingLat', 0)
                if lat:
                    value = str(lat)
        except Exception as e:
            self.logger.info(str(e))
        return value
    

    def get_pdp_lon(self, room_data):
        value = str()
        try:
            meta_data = room_data.get('sections', {}).get('metadata')
            if meta_data:
                event_data = meta_data.get('loggingContext', {}).get('eventDataLogging')
                lon = event_data.get('listingLng', 0)
                if lon:
                    value = str(lon)
        except Exception as e:
            self.logger.info(str(e))
        return value
    

    def get_pdp_capacity(self, room_data):
        value = int()
        try:
            meta_data = room_data.get('sections', {}).get('metadata')
            if meta_data:
                capacity = meta_data.get('sharingConfig', {}).get('personCapacity')
                if capacity:
                    value = capacity
        except Exception as e:
            self.logger.info(str(e))
        return value
    
    
    def get_pdp_rooms(self, room_data):
        value = {
            'bedroom': 0,
            'bath': 0,
            'beds': 0
        }
        try:
            sbui_data = room_data.get('sections', {}).get('sbuiData')
            if sbui_data:
                sections = sbui_data.get('sectionConfiguration', {}).get('root', {}).get('sections',[])
                for section in sections:
                    if section.get('sectionId') == 'OVERVIEW_DEFAULT_V2':
                        sec_data = section.get('sectionData')
                        overview_items = sec_data.get('overviewItems', [])
                        if overview_items:
                            keys = list(value)
                            for key in keys:
                                room = [room.get('title') for room in overview_items if key in room.get('title')]
                                if room:
                                    room_txt = room[0]
                                    matches = re.search(r'([0-9+]+)', room_txt)
                                    if matches:
                                        value.update({key: matches.group(1)})
        except Exception as e:
            self.logger.info(str(e))
        return value
    
    
    def get_pdp_fees(self, room_data):
        value = {
            'cleaning_fee':0,
            'service_fee':0
        }
        try:
            sections = room_data.get('sections', {}).get('sections')
            if sections:
                for section in sections:
                    if section.get('sectionComponentType') == 'BOOK_IT_CALENDAR_SHEET':
                        sec_data = section.get('section')
                        price_items = sec_data.get('structuredDisplayPrice', {}).get('explanationData', {}).get('priceDetails', [None])[0].get('items')
                        fees = list(value)
                        if price_items:
                            for key in fees:
                                fee = ' '.join(key.split('_'))
                                item = [item.get('priceString') for item in price_items if fee in item.get('description').lower()]
                                if item:
                                    fee_val = float(re.sub('[^0-9.]', '', item[0]))
                                    if fee_val:
                                        value.update({key: fee_val})

        except Exception as e:
            self.logger.info(str(e))
        return value

    
    def get_property_type(self, room_data):
        value = str()
        try:
            meta_data = room_data.get('sections', {}).get('metadata')
            if meta_data:
                property_type = meta_data.get('sharingConfig', {}).get('propertyType')
                if property_type:
                    value = property_type
        except Exception as e:
            self.logger.info(str(e))
        return value

    
    def get_pdp_amenties(self, room_data):
        value = {
            'kitchen': False,
            'pool': False,
            'extra': []
        }
        try:
            extras = []
            sections = room_data.get('sections', {}).get('sections',[])
            if sections:
                for section in sections:
                    if section.get('sectionId') == 'AMENITIES_DEFAULT':
                        all_amenities_group = section.get('section', {}).get('seeAllAmenitiesGroups')
                        if all_amenities_group:
                            for group in all_amenities_group:
                                amenties = group.get('amenities', [])
                                for item in amenties:
                                    if 'kitchen' in item.get('title').lower():
                                        available = item.get('available', False)
                                        value.update({'kitchen': available})
                                    elif 'pool' in item.get('title').lower():
                                        available = item.get('available', False)
                                        value.update({'pool': available})
                                    else:
                                        title = item.get('title')
                                        if item.get('available', False):
                                            extras.append(title)
                                            
            if extras:
                value.update({'extra': extras})
        except Exception as e:
            self.logger.info(str(e))
        return value
    

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


    def fetch_pdp_price_data(self, url, soup):
        data = {}

        try:
            api_url = self.generate_pdp_checkout_api_url(soup)
            headers = self.generate_pdp_api_headers(soup, url)
            raw = download(api_url, headers=headers)
            if raw:
                _json = json.loads(raw)
                price_data_json = _json.get('data', {}).get('presentation', {}).get('stayCheckout')
                price_per_night = self.get_pdp_price_per_night(price_data_json)
                total_price_per_night = self.get_pdp_total_price(price_data_json)

                data = {
                    "price_per_night": price_per_night,
                    "orig_price_per_night": total_price_per_night
                }


        except Exception as e:
            self.logger.info(str(e))
        return data


    def generate_pdp_price_api_url(self, room_data):

        product_id = self.get_pdp_product_id(room_data)
        parsed = urlparse(self.origin_url)
        parsed_query = parse_qs(parsed.query)
        checkin_date = parsed_query.get('check_in')
        checkout_date = parsed_query.get('check_out')

        query_params = {"operationName": "stayCheckout",
            "locale": "en",
            "currency": "USD",
            "variables": {
            "input":{
                "businessTravel":{
                    "workTrip":False
                },
                "checkinDate":checkin_date,
                "checkoutDate":checkout_date,
                "guestCounts":{
                    "numberOfAdults":10,
                    "numberOfChildren":0,
                    "numberOfInfants":0,
                    "numberOfPets":0
                },
                "guestCurrencyOverride":"USD",
                "listingDetail":{
                    
                },
                "lux":{
                    
                },
                "metadata":{
                    "internalFlags":[
                        "LAUNCH_LOGIN_PHONE_AUTH"
                    ]
                },
                "org":{
                    
                },
                "productId":product_id,
                "addOn":{
                    "carbonOffsetParams":{
                        "isSelected":False
                    }
                },
                "quickPayData":None
            },
            "isLeanFragment":False
            },
            "extensions": {"persistedQuery":{"version":1,"sha256Hash":"b69ff2a5e43ee3454cb5bcd5bada4c72ad093d6fb57c90a4a7fc4e30490ae7fa"}}

        }

    def get_pdp_product_id(self, room_data):
        try:
            sbui_data = room_data.get('sections', {}).get('sbuiData')
            if sbui_data:
                sections = sbui_data.get('sectionConfiguration', {}).get('root', {}).get('sections',[])
                for section in sections:
                    if section and 'OVERVIEW_DEFAULT_V2' in section.get('sectionId'):
                        product_id = section.get('loggingData', {}).get('eventData', {}).get('productId')
                        if product_id:
                            return product_id
        except Exception as e:
            self.logger.info(str(e))
        return None

