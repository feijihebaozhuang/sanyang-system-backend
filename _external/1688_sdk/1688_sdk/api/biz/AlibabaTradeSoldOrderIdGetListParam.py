# -*- coding: utf-8 -*-
from aop.api.base import BaseApi

class AlibabaTradeSoldOrderIdGetListParam(BaseApi):
    """根据收件人信息（订单创建时间、姓名、手机号、电话）查询1688订单号(卖家视角)


    References
    ----------
    https://open.1688.com/api/api.htm?ns=com.alibaba.trade&n=alibaba.trade.soldOrderId.getList&v=1&cat=aop.trade

    """

    def __init__(self, domain=None):
        BaseApi.__init__(self, domain)
        self.access_token = None
        self.createStart = None
        self.createEnd = None
        self.name = None
        self.mobilePhone = None
        self.status = None
        self.pageIndex = None
        self.pageSize = None

    def get_api_uri(self):
        return '1/com.alibaba.trade/alibaba.trade.soldOrderId.getList'

    def get_required_params(self):
        return ['createStart', 'createEnd', 'name', 'mobilePhone', 'status', 'pageIndex', 'pageSize']

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
