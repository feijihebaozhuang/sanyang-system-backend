# -*- coding: utf-8 -*-
from aop.api.base import BaseApi

class WaybillQueryQueryByWaybillCodesParam(BaseApi):
    """面单详情查询（根据面单号查询）


    """

    def __init__(self, domain=None):
        BaseApi.__init__(self, domain)
        self.access_token = None
        self.request = None
        self.clientAppInfo = None

    def get_api_uri(self):
        return '1/com.alibaba.logistics/waybill.query.queryByWaybillCodes'

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
