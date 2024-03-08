from abc import ABCMeta, abstractmethod


class AbstractCrawler(metaclass=ABCMeta):

    @abstractmethod
    def execute(self, config):
        raise NotImplementedError
