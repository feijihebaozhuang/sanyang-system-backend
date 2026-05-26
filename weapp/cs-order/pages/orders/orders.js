const api = require('../../utils/api');

const STATUS = {
  pending_review: '待审核',
  approved: '已通过',
  rejected: '已驳回',
  in_production: '生产中',
  completed: '已完成',
};

Page({
  data: { orders: [], tab: 'pending_review' },

  onShow() {
    if (!api.getAuth()) {
      wx.redirectTo({ url: '/pages/login/login' });
      return;
    }
    this.load();
  },

  switchTab(e) {
    this.setData({ tab: e.currentTarget.dataset.tab }, () => this.load());
  },

  load() {
    api.listOrders(this.data.tab).then((res) => {
      const items = (res.items || []).map((o) => ({
        ...o,
        statusLabel: STATUS[o.status] || o.status,
        spec: o.length + '×' + o.width + '×' + o.height,
      }));
      this.setData({ orders: items });
    });
  },

  goDetail(e) {
    wx.navigateTo({ url: '/pages/detail/detail?id=' + e.currentTarget.dataset.id });
  },

  logout() {
    api.clearAuth();
    wx.redirectTo({ url: '/pages/login/login' });
  },
});
