# -*- coding: utf-8 -*-
from aop.api.base import BaseApi

class SellerContractQueryParam(BaseApi):
    """卖家查询合约信息

    References
    ----------
    https://open.1688.com/api/api.htm?ns=com.alibaba.trade&n=seller.contract.query&v=1&cat=

    """

    def __init__(self, domain=None):
        BaseApi.__init__(self, domain)
        self.access_token = None
        self.contractId = None
        self.buyerOpenUid = None

    def get_api_uri(self):
        return '1/com.alibaba.trade/seller.contract.query'

    def get_required_params(self):
        return ['contractId', 'buyerOpenUid']

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
