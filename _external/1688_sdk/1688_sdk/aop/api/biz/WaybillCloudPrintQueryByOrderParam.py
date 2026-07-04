# -*- coding: utf-8 -*-
from aop.api.base import BaseApi

class WaybillCloudPrintQueryByOrderParam(BaseApi):
    """根据订单号查询面单信息


    """

    def __init__(self, domain=None):
        BaseApi.__init__(self, domain)
        self.access_token = None
        self.request = None
        self.clientAppInfo = None

    def get_api_uri(self):
        return '1/com.alibaba.logistics/waybill.cloudPrint.queryByOrder'

    def get_required_params(self):
        return ['request', 'clientAppInfo']

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
