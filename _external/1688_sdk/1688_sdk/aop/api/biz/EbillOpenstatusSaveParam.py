# -*- coding: utf-8 -*-
from aop.api.base import BaseApi

class EbillOpenstatusSaveParam(BaseApi):
    """卖家是否开通下游电子面单
1）要求接入一次性传入历史开通电子面单的卖家和渠道，后面有新增增量信息&修改信息传入。
2）若一个商家支持多渠道，需传不同渠道，分别调用多次接口，渠道名称按规范要求传。目前会校验平台支持的渠道。
3) 如果有商家解除签约电子面单，需要传入N。
4）调用需判断接口是否成功，关注业务成功字段，即result.result的值是否为true


    """

    def __init__(self, domain=None):
        BaseApi.__init__(self, domain)
        self.access_token = None
        self.channel = None
        self.ebillOpenStatus = None
        self.weiXinSellerAccount = None

    def get_api_uri(self):
        return '1/com.alibaba.logistics/ebill.openstatus.save'

    def get_required_params(self):
        return ['channel', 'ebillOpenStatus', 'weiXinSellerAccount']

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
