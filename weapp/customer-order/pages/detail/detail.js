const api = require('../../utils/api');

const STATUS = {
  pending_review: '待审核',
  approved: '已通过',
  rejected: '已驳回',
  in_production: '生产中',
  completed: '已完成',
};

Page({
  data: { item: null },

  onLoad(q) {
    const id = q.id;
    api.ensureLogin().then(() => api.getOrder(id)).then((res) => {
      if (res.success) {
        const o = res.item;
        o.statusLabel = STATUS[o.status] || o.status;
        this.setData({ item: o });
      }
    });
  },
});
