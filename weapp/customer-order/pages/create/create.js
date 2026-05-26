const api = require('../../utils/api');

const MAT_MAP = {
  zhengsquare: ['d6d', 'taiwan', 'w7w', 'black', 'red'],
  daikou: ['d6d', 'taiwan', 'w7w', 'black', 'red'],
  juxing: ['b_keng', 'b3b', 'b5b'],
  koudi: ['p6d', 'white', 'black', 'red'],
  shuangcha: ['p6d', 'white', 'black', 'red'],
  zhenzhenmian: ['pe'],
};

Page({
  data: {
    code: '',
    name: '',
    length: '',
    width: '',
    height: '',
    material: 'd6d',
    materialName: '',
    materials: [],
    dimKind: 'outer',
    qty: 1000,
    matchText: '',
    quoteText: '',
    submitting: false,
    error: '',
    isPe: false,
  },

  onLoad(q) {
    const code = decodeURIComponent(q.code || 'zhengsquare');
    const name = decodeURIComponent(q.name || '产品');
    const isPe = code === 'zhenzhenmian';
    wx.setNavigationBarTitle({ title: name });
    this.setData({ code, name, isPe });
    this.loadMaterials(code);
  },

  loadMaterials(code) {
    api.fetchQuoteData().then((res) => {
      if (!res.success || !res.data) return;
      const cfg = res.data;
      getApp().globalData.quoteConfig = cfg;
      let list = [];
      if (code === 'zhenzhenmian' || code === 'pe') {
        list = [{ key: 'pe', name: '珍珠棉' }];
      } else if (code === 'juxing') {
        const m = cfg.materials && cfg.materials.carton && cfg.materials.carton.materials;
        list = m ? Object.keys(m).map((k) => ({ key: k, name: m[k].name })) : [];
      } else if (code === 'koudi' || code === 'shuangcha') {
        const m = cfg.materials && cfg.materials.koudi && cfg.materials.koudi.materials;
        const order = MAT_MAP.koudi;
        list = order.filter((k) => m && m[k]).map((k) => ({ key: k, name: m[k].name }));
      } else {
        const m = cfg.materials && cfg.materials.airbox && cfg.materials.airbox.materials;
        const order = MAT_MAP.zhengsquare;
        list = order.filter((k) => m && m[k]).map((k) => ({ key: k, name: m[k].name }));
      }
      const material = (list[0] && list[0].key) || 'd6d';
      this.setData({
        materials: list,
        material,
        materialName: list[0] ? list[0].name : '',
      });
    });
  },

  onInput(e) {
    this.setData({ [e.currentTarget.dataset.field]: e.detail.value });
  },

  onMat(e) {
    const key = e.currentTarget.dataset.key;
    const name = e.currentTarget.dataset.name;
    this.setData({ material: key, materialName: name });
  },

  onDim(e) {
    this.setData({ dimKind: e.detail.value });
  },

  doMatch() {
    const { code, length, width, height, material, dimKind } = this.data;
    api
      .matchSku({
        product_category_code: code,
        length: parseFloat(length),
        width: parseFloat(width),
        height: parseFloat(height),
        material,
        dim_kind: dimKind,
      })
      .then((res) => {
        if (res.matched && res.match) {
          this.setData({
            matchText: '已匹配 SKU：' + res.match.outer_id + ' ' + (res.match.km_title || ''),
          });
        } else {
          this.setData({ matchText: '未匹配到现有 SKU，提交后由客服审核' });
        }
      })
      .catch((e) => this.setData({ error: e.message }));
  },

  doQuote() {
    const { code, length, width, height, material, qty, isPe } = this.data;
    api
      .calculateQuote({
        product_category_code: code,
        length: parseFloat(length),
        width: parseFloat(width),
        height: parseFloat(height),
        material,
        qty: parseInt(qty, 10) || 1000,
        discount: 100,
      })
      .then((res) => {
        if (res.success === false || res.error) {
          this.setData({ error: res.error || '算价失败' });
          return;
        }
        const d = res.detail || res;
        const price = d.total_price || d.totalPrice || (d.sell_price_per_unit && d.qty ? d.sell_price_per_unit * d.qty : '');
        this.setData({
          quoteText: price ? '参考价：¥' + Number(price).toFixed(2) : JSON.stringify(d).slice(0, 120),
          quoteDetail: d,
          error: '',
        });
      })
      .catch((e) => this.setData({ error: e.message }));
  },

  submitOrder() {
    const { code, length, width, height, material, dimKind, qty, quoteDetail } = this.data;
    if (!length || !width || !height) {
      this.setData({ error: '请填写完整规格' });
      return;
    }
    this.setData({ submitting: true, error: '' });
    const unit = quoteDetail && quoteDetail.sell_price_per_unit ? quoteDetail.sell_price_per_unit : 0;
    const total = quoteDetail && quoteDetail.total_price ? quoteDetail.total_price : unit * qty;
    api
      .ensureLogin()
      .then(() =>
        api.createOrder({
          product_category_code: code,
          length: parseFloat(length),
          width: parseFloat(width),
          height: parseFloat(height),
          material,
          dim_kind: dimKind,
          qty: parseInt(qty, 10) || 1,
          unit_price: unit,
          total_price: total,
          status: 'pending_review',
        })
      )
      .then((res) => {
        this.setData({ submitting: false });
        if (!res.success) throw new Error(res.error || '下单失败');
        wx.showToast({ title: '已提交' });
        wx.redirectTo({ url: '/pages/detail/detail?id=' + res.item.id });
      })
      .catch((e) => this.setData({ submitting: false, error: e.message }));
  },
});
