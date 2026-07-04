# -*- coding: utf-8 -*-
from aop.api.base import BaseApi

class AlibabaLogisticsOpDeliverySendOrderDummyParam(BaseApi):
    """1688大市场订单，无需物流，支持合并发货，即：多个订单一次发货；支持子订单(orderEntry)级别的发货，不支持按数量发货。

    References
    ----------
    https://open.1688.com/api/api.htm?ns=com.alibaba.logistics&n=alibaba.logistics.OpDeliverySendOrder.dummy&v=1&cat=wuliu

    """

    def __init__(self, domain=None):
        BaseApi.__init__(self, domain)
        self.access_token = None
        self.sendGoods = None
        self.remarks = None
        self.gmtSend = None
        self.extBody = None
        self.extParam = None
        self.receiverInfo = None

    def get_api_uri(self):
        return '1/com.alibaba.logistics/alibaba.logistics.OpDeliverySendOrder.dummy'

    def get_required_params(self):
        return ['sendGoods', 'remarks', 'gmtSend', 'extBody', 'extParam', 'receiverInfo']

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
