# -*- coding: utf-8 -*-
from aop.api.base import BaseApi

class AlibabaTradeSoldOrderIdMergeParam(BaseApi):
    """输入caidBase合订单号，收件人地址相同的订单号会归成一组

    References
    ----------
    https://open.1688.com/api/api.htm?ns=com.alibaba.logistics&n=alibaba.trade.soldOrderId.merge&v=1&cat=aop.logistics

    """

    def __init__(self, domain=None):
        BaseApi.__init__(self, domain)
        self.access_token = None
        self.items = None

    def get_api_uri(self):
        return '1/com.alibaba.logistics/alibaba.trade.soldOrderId.merge'

    def get_required_params(self):
        return ['items']

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
