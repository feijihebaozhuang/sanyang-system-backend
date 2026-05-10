# -*- coding: utf-8 -*-
from aop.api.base import BaseApi

class AlibabaTradeEcGetOrderListSellerViewParam(BaseApi):
    """获取卖家订单列表，也就是用户的memberId必须等于订单的sellerMemberId。该接口仅仅返回订单基本信息，不会返回订单的物流信息和发票信息；如果需要获取物流信息，请调用获取订单详情接口；如果需要获取发票信息，请调用获取发票信息的API

    References
    ----------
    https://open.1688.com/api/api.htm?ns=com.alibaba.trade&n=alibaba.trade.ec.getOrderList.sellerView&v=1&cat=aop.trade

    """

    def __init__(self, domain=None):
        BaseApi.__init__(self, domain)
        self.access_token = None
        self.createStartTime = None
        self.createEndTime = None
        self.modifyStartTime = None
        self.modifyEndTime = None
        self.page = None
        self.pageSize = None
        self.orderStatus = None
        self.refundStatus = None
        self.buyerMemberId = None
        self.buyerLoginId = None
        self.tradeType = None
        self.bizTypes = None
        self.isHis = None
        self.productName = None
        self.needBuyerAddressAndPhone = None
        self.needMemoInfo = None
        self.tousuStatus = None
        self.buyerRateStatus = None
        self.sellerRateStatus = None
        self.needCheckSend = None
        self.needOutChannel = None
        self.needSendGoodsOverdueRisk = None
        self.needDeliverGoodsOverdueRisk = None
        self.needOfficialLogisticOrder = None
        self.needTgOfficialPickUpOrder = None

    def get_api_uri(self):
        return '1/com.alibaba.trade/alibaba.trade.ec.getOrderList.sellerView'

    def get_required_params(self):
        return ['createStartTime', 'createEndTime', 'modifyStartTime', 'modifyEndTime', 'page', 'pageSize', 'orderStatus', 'refundStatus', 'buyerMemberId', 'buyerLoginId', 'tradeType', 'bizTypes', 'isHis', 'productName', 'needBuyerAddressAndPhone', 'needMemoInfo', 'tousuStatus', 'buyerRateStatus', 'sellerRateStatus', 'needCheckSend', 'needOutChannel', 'needSendGoodsOverdueRisk', 'needDeliverGoodsOverdueRisk', 'needOfficialLogisticOrder', 'needTgOfficialPickUpOrder']

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
