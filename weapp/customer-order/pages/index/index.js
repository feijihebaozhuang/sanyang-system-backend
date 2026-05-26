const api = require('../../utils/api');

Page({
  data: {
    loading: true,
    categories: [],
    error: '',
  },

  onShow() {
    this.load();
  },

  load() {
    this.setData({ loading: true, error: '' });
    api
      .ensureLogin()
      .then(() => api.fetchCategories())
      .then((res) => {
        if (!res.success) throw new Error(res.error || '加载失败');
        this.setData({ categories: res.items || [], loading: false });
        getApp().globalData.categories = res.items || [];
      })
      .catch((e) => {
        this.setData({ loading: false, error: e.message || '加载失败' });
      });
  },

  goCreate(e) {
    const code = e.currentTarget.dataset.code;
    const name = e.currentTarget.dataset.name;
    wx.navigateTo({
      url: '/pages/create/create?code=' + encodeURIComponent(code) + '&name=' + encodeURIComponent(name),
    });
  },

  goOrders() {
    wx.navigateTo({ url: '/pages/orders/orders' });
  },
});
