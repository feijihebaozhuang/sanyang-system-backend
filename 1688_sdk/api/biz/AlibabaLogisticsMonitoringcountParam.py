# -*- coding: utf-8 -*-
from aop.api.base import BaseApi

class AlibabaLogisticsMonitoringcountParam(BaseApi):
    """查询物流监控异常数量统计


    """

    def __init__(self, domain=None):
        BaseApi.__init__(self, domain)
        self.access_token = None
        self.arg0 = None

    def get_api_uri(self):
        return '1/com.alibaba.logistics/alibaba.logistics.monitoringcount'

    def get_required_params(self):
        return ['arg0']

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
