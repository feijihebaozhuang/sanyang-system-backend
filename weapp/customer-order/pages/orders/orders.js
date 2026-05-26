const api = require('../../utils/api');

const STATUS = {
  draft: '草稿',
  pending_review: '待审核',
  approved: '已通过',
  rejected: '已驳回',
  in_production: '生产中',
  completed: '已完成',
  cancelled: '已取消',
};

Page({
  data: { orders: [], loading: true },

  onShow() {
    this.load();
  },

  load() {
    api
      .ensureLogin()
      .then(() => api.listOrders())
      .then((res) => {
        const items = (res.items || []).map((o) => ({
          ...o,
          statusLabel: STATUS[o.status] || o.status,
          spec: o.length + '×' + o.width + '×' + o.height,
        }));
        this.setData({ orders: items, loading: false });
      })
      .catch(() => this.setData({ loading: false }));
  },

  goDetail(e) {
    wx.navigateTo({ url: '/pages/detail/detail?id=' + e.currentTarget.dataset.id });
  },
});
