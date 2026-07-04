# -*- coding: utf-8 -*-
from aop.api.base import BaseApi

class AlibabaTradeLogisticsRecevierDecryptParam(BaseApi):
    """输入caid和订单id，用以获取买家收件人信息

    References
    ----------
    https://open.1688.com/api/api.htm?ns=com.alibaba.logistics&n=alibaba.trade.logisticsRecevier.decrypt&v=1&cat=my_logistics_meta

    """

    def __init__(self, domain=None):
        BaseApi.__init__(self, domain)
        self.access_token = None
        self.orderId = None
        self.caid = None

    def get_api_uri(self):
        return '1/com.alibaba.logistics/alibaba.trade.logisticsRecevier.decrypt'

    def get_required_params(self):
        return ['orderId', 'caid']

    def get_multipart_params(self):
        return []

    def need_sign(self):
        return True

    def need_timestamp(self):
        return False

    def need_auth(self):
        return True

    def need_https(self):
        return False

    def is_inner_api(self):
        return False
