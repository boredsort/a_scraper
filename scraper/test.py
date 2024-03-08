from scraper.factory import StrategyFactory
import logging

website = 'www.airbnb.com'
# url = 'https://www.airbnb.com/rooms/47723136?adults=1&category_tag=Tag%3A8536&children=0&enable_m3_private_room=true&infants=0&pets=0&photo_id=1141067617&search_mode=flex_destinations_search&check_in=2024-03-17&check_out=2024-03-22&source_impression_id=p3_1709044046_TbBuxJNNYSVzMfQZ&previous_page_section_name=1000&federated_search_id=24353795-85ab-466d-bd81-9d8ae9d74ef4'
url = 'https://www.airbnb.com/s/Kissimmee--Florida--United-States/homes?tab_id=home_tab&refinement_paths%5B%5D=%2Fhomes&flexible_trip_lengths%5B%5D=one_week&monthly_start_date=2024-03-01&monthly_length=3&monthly_end_date=2024-06-01&price_filter_input_type=0&channel=EXPLORE&query=Kissimmee%2C%20Florida%2C%20United%20States&place_id=ChIJ5wsVNxqE3YgRDcL9EZfN55Q&date_picker_type=calendar&checkin=2024-03-26&checkout=2024-03-30&source=structured_search_input_header&search_type=autocomplete_click'

strategy = StrategyFactory().get_strategy(website, 'Search')(logging.getLogger())
config = {
    "url": url
}
logging.basicConfig(level = logging.INFO)
strategy.execute(config)
