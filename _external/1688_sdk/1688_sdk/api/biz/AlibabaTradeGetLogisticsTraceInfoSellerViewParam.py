# -*- coding: utf-8 -*-
from aop.api.base import BaseApi

class AlibabaTradeGetLogisticsTraceInfoSellerViewParam(BaseApi):
    """获取卖家的订单的物流跟踪信息。该接口能查能根据物流单号查看物流单跟踪信息。由于物流单录入的原因，可能跟踪信息的API查询会有延迟。

    References
    ----------
    https://open.1688.com/api/api.htm?ns=com.alibaba.logistics&n=alibaba.trade.getLogisticsTraceInfo.sellerView&v=1&cat=wuliu

    """

    def __init__(self, domain=None):
        BaseApi.__init__(self, domain)
        self.access_token = None
        self.logisticsId = None
        self.orderId = None
        self.webSite = None

    def get_api_uri(self):
        return '1/com.alibaba.logistics/alibaba.trade.getLogisticsTraceInfo.sellerView'

    def get_required_params(self):
        return ['logisticsId', 'orderId', 'webSite']

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
