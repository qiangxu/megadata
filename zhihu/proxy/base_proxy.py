import json
from abc import ABC, abstractmethod
from typing import List

import config
from caches.abs_cache import AbstractCache
from caches.cache_factory import CacheFactory
from tools.utils import utils

from .types import IpInfoModel


class IpGetError(Exception):
    """ ip get error"""


class ProxyProvider(ABC):
    @abstractmethod
    async def get_proxies(self, num: int) -> List[IpInfoModel]:
        """
        获取 IP 的抽象方法，不同的 HTTP 代理商需要实现该方法
        :param num: 提取的 IP 数量
        :return:
        """
        raise NotImplementedError



class IpCache:
    def __init__(self):
        self.cache_client: AbstractCache = CacheFactory.create_cache(cache_type=config.CACHE_TYPE_MEMORY)

    def set_ip(self, ip_key: str, ip_value_info: str, ex: int):
        """
        设置IP并带有过期时间，到期之后由 redis 负责删除
        :param ip_key:
        :param ip_value_info:
        :param ex:
        :return:
        """
        self.cache_client.set(key=ip_key, value=ip_value_info, expire_time=ex)

    def load_all_ip(self, proxy_brand_name: str) -> List[IpInfoModel]:
        """
        从 redis 中加载所有还未过期的 IP 信息
        :param proxy_brand_name: 代理商名称
        :return:
        """
        all_ip_list: List[IpInfoModel] = []
        all_ip_keys: List[str] = self.cache_client.keys(pattern=f"{proxy_brand_name}_*")
        try:
            for ip_key in all_ip_keys:
                ip_value = self.cache_client.get(ip_key)
                if not ip_value:
                    continue
                all_ip_list.append(IpInfoModel(**json.loads(ip_value)))
        except Exception as e:
            utils.logger.error("[IpCache.load_all_ip] get ip err from redis db", e)
        return all_ip_list
