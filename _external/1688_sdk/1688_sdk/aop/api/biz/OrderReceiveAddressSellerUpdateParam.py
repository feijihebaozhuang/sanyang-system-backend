# -*- coding: utf-8 -*-
from aop.api.base import BaseApi

class OrderReceiveAddressSellerUpdateParam(BaseApi):
    """卖家修改订单的收货地址


    """

    def __init__(self, domain=None):
        BaseApi.__init__(self, domain)
        self.access_token = None
        self.param = None

    def get_api_uri(self):
        return '1/com.alibaba.trade/order.receiveAddress.sellerUpdate'

    def get_required_params(self):
        return ['param']

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
