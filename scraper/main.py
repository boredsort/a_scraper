import logging
import os
import csv
import json
from datetime import datetime
from urllib.parse import urlparse

from scraper.utils.url_generator import generate_query_url
from scraper.factory import StrategyFactory

output_path = 'output'
target_file = 'target_profiles.json'

logger = logging.getLogger()
def execute(config):
    
    path_to_file = os.path.dirname(__file__)


    results = []
    crawl_data = {}
    profile = config.get('property_preset')
    url = profile.get('url')
    parsed = urlparse(url)
    website = parsed.netloc
    strategy = StrategyFactory().get_strategy(website, 'Search')(logger=logger)
    query = profile.get('query')
    if query:
        url = generate_query_url(url, **query)
    crawl_started = str(datetime.now())
    data = strategy.execute(config={"url": url})
    crawl_finished = str(datetime.now())
    timestamp = int(datetime.timestamp(datetime.now()))
    items_data = [item for items in data for item in items]
    crawl_data = {
        "url": url,
        "file": f"{timestamp}.json",
        "crawl_start": crawl_started ,
        "crawl_finish": crawl_finished,
        "result": items_data,
    }
    # items_data = [item for items in data for item in items]

    results.append(crawl_data)

    target_out_file_path = os.path.join(path_to_file, output_path)
    output_dir_exists = os.path.exists(target_out_file_path)
    if not output_dir_exists:
        os.makedirs(target_out_file_path)
    

    with open(f'{target_out_file_path}/{timestamp}.json', 'w', encoding='UTF-8' ) as file:
        logger.info(f'[*] Writing to file: {timestamp}.json')
        file.write(json.dumps(crawl_data, indent=4))

    file_title = '_'.join(profile.get('label','').lower().split()) + f'_{timestamp}'
    with open(f'{target_out_file_path}/{file_title}.csv', 'w', encoding='UTF-8',newline='' ) as file:
        logger.info(f'[*] Writing to file: {file_title}.csv')
        headers = list(items_data[0].keys())
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        writer.writerows(items_data)

    return crawl_data

