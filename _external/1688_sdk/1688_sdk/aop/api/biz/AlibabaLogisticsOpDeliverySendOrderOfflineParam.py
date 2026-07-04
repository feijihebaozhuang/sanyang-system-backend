# -*- coding: utf-8 -*-
from aop.api.base import BaseApi

class AlibabaLogisticsOpDeliverySendOrderOfflineParam(BaseApi):
    """1688大市场订单，卖家自己联系物流发货，支持合并发货，即：多个订单一次发货；支持子订单(orderEntry)级别的发货，不支持按数量发货。

    References
    ----------
    https://open.1688.com/api/api.htm?ns=com.alibaba.logistics&n=alibaba.logistics.OpDeliverySendOrder.offline&v=1&cat=aop.logistics

    """

    def __init__(self, domain=None):
        BaseApi.__init__(self, domain)
        self.access_token = None
        self.multiPackage = None
        self.sendGoods = None
        self.remarks = None
        self.gmtSend = None
        self.extBody = None
        self.extParam = None
        self.receiverInfo = None
        self.isEncryptOrderSend = None

    def get_api_uri(self):
        return '1/com.alibaba.logistics/alibaba.logistics.OpDeliverySendOrder.offline'

    def get_required_params(self):
        return ['multiPackage', 'sendGoods', 'remarks', 'gmtSend', 'extBody', 'extParam', 'receiverInfo', 'isEncryptOrderSend']

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
