from urllib.parse import urlparse, urlencode, quote, parse_qs, urlunparse
from dateutil import parser



def generate_query_url(url, **kwargs):

    params_keys = {
        "bedroom": "min_bedrooms",
        "checkin": "checkin",
        "checkout": "checkout",
        "bed": "min_beds",
        "price_min": "price_min",
        "price_max": "price_max",
        "adults": "adults",
        "pool": "amenities[]",
        "waterfront":"kg_and_tags[]"
    }
    queries = {}
    for key, query_key in params_keys.items():
        value = kwargs.get(key)
        if value:
            if 'checkin' in key or 'checkout' in key:
                value = date_formater(value)
            if 'pool' in key and 'true' in value.lower():
                value = '7'
            if 'waterfront' in key and 'true' in value.lower():
                value = 'Tag:686'
            queries.update({query_key: [str(value)]})

    parsed = urlparse(url)
    parsed_query = parse_qs(parsed.query)
    parsed_query.update(queries)
    updated_query = urlencode(parsed_query, doseq=True, quote_via=quote)
    updated_parsed = parsed._replace(query=updated_query)
    
    return urlunparse(updated_parsed)


def date_formater(date_string):
    parsed = parser.parse(date_string)
    return parsed.strftime('%Y-%m-%d')