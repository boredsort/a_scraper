import re
import importlib
import os



class StrategyFactory:
    
    def get_strategy(self, website, page_type):
        
        try:
            website = website.lower()
            page_type = page_type.lower()
            folder_name = self._get_folder_name(website)
            module_path = f'scraper.strategies.{folder_name}.{page_type}_page'
            module = importlib.import_module(module_path)
            class_name = f'{self._get_class_name(folder_name)}{page_type.capitalize()}Strategy'
            return getattr(module, class_name)

        except KeyError:
            raise Exception("Failed to find crawler")
        except:
            raise Exception("Unhandled Exception.")


    def _get_folder_name(self, website):
        name = re.sub(r'[^a-z.]', '', website.lower())
        return name.strip('www.').replace('.','_')
    
    def _get_class_name(self, name):

        if not name:
            return None

        name = name.lower()
        splited_name = name.split('_')

        class_name = ''
        for word in splited_name:
            class_name += word.capitalize()

        return class_name