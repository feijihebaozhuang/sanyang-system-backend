# -*- coding: utf-8 -*-
from aop.api.base import BaseApi

class AlibabaTradeRefundOpQueryBatchRefundByOrderIdAndStatusSellerViewParam(BaseApi):
    """根据订单号实时查询退款单列表，目前只能查询到售中的退款单

    References
    ----------
    https://open.1688.com/api/api.htm?ns=com.alibaba.trade&n=alibaba.trade.refund.OpQueryBatchRefundByOrderIdAndStatus.sellerView&v=1&cat=aop.trade

    """

    def __init__(self, domain=None):
        BaseApi.__init__(self, domain)
        self.access_token = None
        self.orderId = None
        self.queryType = None

    def get_api_uri(self):
        return '1/com.alibaba.trade/alibaba.trade.refund.OpQueryBatchRefundByOrderIdAndStatus.sellerView'

    def get_required_params(self):
        return ['orderId', 'queryType']

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
