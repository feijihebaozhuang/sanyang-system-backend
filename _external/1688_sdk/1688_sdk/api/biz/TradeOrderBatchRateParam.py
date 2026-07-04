# -*- coding: utf-8 -*-
from aop.api.base import BaseApi

class TradeOrderBatchRateParam(BaseApi):
    """此接口支持多笔订单（暂定最多10笔每次）同时提交评价，并且只支持卖家向买家的评价，目前当某笔订单存在多个商品时,只能为这笔订单的这些商品提交相同的评价内容。

    References
    ----------
    https://open.1688.com/api/api.htm?ns=cn.alibaba.open&n=trade.order.batch.rate&v=1&cat=trade(new)

    """

    def __init__(self, domain=None):
        BaseApi.__init__(self, domain)
        self.access_token = None
        self.orders = None

    def get_api_uri(self):
        return '1/cn.alibaba.open/trade.order.batch.rate'

    def get_required_params(self):
        return ['orders']

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
