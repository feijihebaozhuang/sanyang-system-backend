const { API_BASE } = require('../config');

const AUTH_KEY = 'sy_co_auth';

function getAuth() {
  try {
    return wx.getStorageSync(AUTH_KEY) || null;
  } catch (e) {
    return null;
  }
}

function setAuth(auth) {
  wx.setStorageSync(AUTH_KEY, auth);
}

function clearAuth() {
  wx.removeStorageSync(AUTH_KEY);
}

function request(path, options) {
  const auth = getAuth();
  const header = {
    'content-type': 'application/json',
    ...(options && options.header),
  };
  if (auth) {
    header.Authorization = 'Bearer ' + auth.token;
    header['X-Mp-Openid'] = auth.openid;
    header['X-Mp-Customer-Id'] = String(auth.customer_id);
    header['X-Mp-Token'] = auth.token;
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

function wxLogin() {
  return new Promise((resolve, reject) => {
    wx.login({
      success(r) {
        if (!r.code) reject(new Error('wx.login 无 code'));
        else resolve(r.code);
      },
      fail: reject,
    });
  });
}

function ensureLogin() {
  const auth = getAuth();
  if (auth && auth.token) return Promise.resolve(auth);
  return wxLogin().then((code) =>
    request('/api/mp/wx/login', { method: 'POST', data: { code } }).then((res) => {
      if (!res.success) throw new Error(res.error || '登录失败');
      const a = {
        openid: res.openid,
        customer_id: res.customer_id,
        token: res.token,
        customer: res.customer,
      };
      setAuth(a);
      return a;
    })
  );
}

module.exports = {
  API_BASE,
  request,
  ensureLogin,
  getAuth,
  setAuth,
  clearAuth,
  fetchCategories: () => request('/api/mp/categories'),
  fetchQuoteData: () => request('/api/mp/quote_data'),
  calculateQuote: (data) => request('/api/mp/quote/calculate', { method: 'POST', data }),
  matchSku: (data) => request('/api/mp/match', { method: 'POST', data }),
  createOrder: (data) => request('/api/mp/order/create', { method: 'POST', data }),
  listOrders: () => request('/api/mp/orders'),
  getOrder: (id) => request('/api/mp/order/' + id),
};
