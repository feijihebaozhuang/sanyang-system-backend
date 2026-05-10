# -*- coding: utf-8 -*-
from aop.api.base import BaseApi

class AlibabaTradeEcGetLogisticsInfosSellerViewParam(BaseApi):
    """获取卖家的订单的物流详情。该接口能查能根据物流单号查看物流详情，包括发件人，收件人，所发货物明细等。由于物流单录入的原因，可能跟踪信息的API查询会有延迟，加密场景使用。

    References
    ----------
    https://open.1688.com/api/api.htm?ns=com.alibaba.logistics&n=alibaba.trade.ec.getLogisticsInfos.sellerView&v=1&cat=aop.logistics

    """

    def __init__(self, domain=None):
        BaseApi.__init__(self, domain)
        self.orderId = None
        self.fields = None
        self.webSite = None

    def get_api_uri(self):
        return '1/com.alibaba.logistics/alibaba.trade.ec.getLogisticsInfos.sellerView'

    def get_required_params(self):
        return ['orderId', 'fields', 'webSite']

    def get_multipart_params(self):
        return []

    def need_sign(self):
        return True

    def need_timestamp(self):
        return False

    def need_auth(self):
        return False

    def need_https(self):
        return False

    def is_inner_api(self):
        return False
