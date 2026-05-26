const api = require('../../utils/api');

Page({
  data: { username: '', password: '', error: '' },

  onLoad() {
    if (api.getAuth()) {
      wx.redirectTo({ url: '/pages/orders/orders' });
    }
  },

  onUser(e) {
    this.setData({ username: e.detail.value });
  },
  onPwd(e) {
    this.setData({ password: e.detail.value });
  },

  login() {
    const { username, password } = this.data;
    api
      .login(username, password)
      .then((res) => {
        if (!res.success) throw new Error(res.error || '登录失败');
        api.setAuth({
          username: res.username,
          token: res.token,
          cs_staff_id: res.cs_staff_id,
          display_name: res.display_name,
        });
        wx.redirectTo({ url: '/pages/orders/orders' });
      })
      .catch((e) => this.setData({ error: e.message }));
  },
});
