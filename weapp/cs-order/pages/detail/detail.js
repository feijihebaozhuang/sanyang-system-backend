const api = require('../../utils/api');

Page({
  data: { item: null, remark: '' },

  onLoad(q) {
    this.orderId = q.id;
    this.load();
  },

  load() {
    const auth = api.getAuth();
    api.listOrders('').then((res) => {
      const item = (res.items || []).find((o) => String(o.id) === String(this.orderId));
      if (item) this.setData({ item, remark: item.remark || '' });
    });
  },

  onRemark(e) {
    this.setData({ remark: e.detail.value });
  },

  review(status) {
    api
      .reviewOrder({ id: this.orderId, status, remark: this.data.remark })
      .then((res) => {
        if (!res.success) throw new Error(res.error);
        wx.showToast({ title: status === 'approved' ? '已通过' : '已驳回' });
        setTimeout(() => wx.navigateBack(), 800);
      })
      .catch((e) => wx.showToast({ title: e.message, icon: 'none' }));
  },

  approve() {
    this.review('approved');
  },
  reject() {
    this.review('rejected');
  },
});
