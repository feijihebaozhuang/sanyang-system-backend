const { API_BASE } = require('../config');
const AUTH_KEY = 'sy_cs_auth';

function getAuth() {
  try {
    return wx.getStorageSync(AUTH_KEY) || null;
  } catch (e) {
    return null;
  }
}

function setAuth(a) {
  wx.setStorageSync(AUTH_KEY, a);
}

function clearAuth() {
  wx.removeStorageSync(AUTH_KEY);
}

function request(path, options) {
  const auth = getAuth();
  const header = { 'content-type': 'application/json', ...(options && options.header) };
  if (auth) {
    header.Authorization = 'Bearer ' + auth.token;
    header['X-Mp-User'] = auth.username;
    header['X-Mp-Token'] = auth.token;
    header['X-Mp-Cs-Id'] = auth.cs_staff_id ? String(auth.cs_staff_id) : '';
  }
  return new Promise((resolve, reject) => {
    wx.request({
      url: API_BASE + path,
      method: (options && options.method) || 'GET',
      data: (options && options.data) || {},
      header,
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) resolve(res.data);
        else reject(new Error((res.data && res.data.error) || 'HTTP ' + res.statusCode));
      },
      fail: reject,
    });
  });
}

module.exports = {
  getAuth,
  setAuth,
  clearAuth,
  login: (username, password) =>
    request('/api/mp/cs/login', { method: 'POST', data: { username, password } }),
  listOrders: (status) =>
    request('/api/mp/cs/orders' + (status ? '?status=' + encodeURIComponent(status) : '')),
  reviewOrder: (data) => request('/api/mp/cs/order/review', { method: 'POST', data }),
  calculateQuote: (data) => request('/api/mp/quote/calculate', { method: 'POST', data }),
};
