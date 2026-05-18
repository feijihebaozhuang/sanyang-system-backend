#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞机盒智能生产管理系统 - 后端API
小马哥专属
"""

from flask import Flask, jsonify, send_from_directory, request, make_response, Response, session
from flask_cors import CORS
import json, datetime, csv, io, os, hashlib, copy, time, re, hmac, urllib.parse, urllib.request
from datetime import timedelta
from pypinyin import lazy_pinyin
import pymysql

from settings import DB_CONFIG, FLASK_SECRET_KEY


def _auth_token_for(username: str) -> str:
    return hashlib.sha256(f"{FLASK_SECRET_KEY}:{username}".encode()).hexdigest()[:32]


def resolve_login_user() -> str | None:
    un = session.get("username")
    if un and un in USERS:
        return un
    hdr_user = (request.headers.get("X-Sanyang-User") or "").strip()
    hdr_tok = (request.headers.get("X-Sanyang-Token") or "").strip()
    if hdr_user in USERS and hdr_tok and hdr_tok == _auth_token_for(hdr_user):
        return hdr_user
    return None


def get_db():
    """获取数据库连接，每次调用新建（线程安全）"""
    return pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)

app = Flask(__name__, static_folder='.')
app.secret_key = FLASK_SECRET_KEY
CORS(app, supports_credentials=True)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=31)
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_REFRESH_EACH_REQUEST'] = True
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', '').lower() in (
    '1', 'true', 'yes'
)

# ==================== 用户系统 ====================
USERS = {
    "admin": {
        "password": hashlib.sha256("admin888".encode()).hexdigest(),
        "name": "戴雅利",
        "role": "超级管理员",
        "employee_name": "戴雅利"
    },
    "manager": {
        "password": hashlib.sha256("manager666".encode()).hexdigest(),
        "name": "邓涛",
        "role": "管理",
        "employee_name": "邓涛"
    },
    "worker": {
        "password": hashlib.sha256("worker123".encode()).hexdigest(),
        "name": "李周海",
        "role": "员工",
        "employee_name": "李周海"
    },
    "sushiting": {
        "password": hashlib.sha256("sushiting123".encode()).hexdigest(),
        "name": "苏世婷",
        "role": "客服",
        "employee_name": "苏世婷"
    },
    "liaosimei": {
        "password": hashlib.sha256("liaosimei123".encode()).hexdigest(),
        "name": "廖思美",
        "role": "客服",
        "employee_name": "廖思美"
    }
}

def require_login():
    """检查是否已登录"""
    if 'username' not in session:
        return jsonify({"error": "未登录", "code": 401}), 401
    return None

def require_admin():
    """检查是否为超级管理员"""
    if 'username' not in session:
        return jsonify({"error": "未登录", "code": 401}), 401
    user = USERS.get(session['username'])
    if not user or user['role'] != '超级管理员':
        return jsonify({"error": "无权限", "code": 403}), 403
    return None

# ==================== 数据持久化 ====================
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data.json')

def load_data():
    """从JSON文件加载持久化数据"""
    # 生成默认用户密码哈希
    default_users = {
        "admin": {
            "password": hashlib.sha256("admin888".encode()).hexdigest(),
            "name": "admin",
            "role": "超级管理员",
            "employee_name": "",
            "is_system": True
        },
        "daiyali": {
            "password": hashlib.sha256("admin888".encode()).hexdigest(),
            "name": "戴雅利",
            "role": "超级管理员",
            "employee_name": "戴雅利"
        },
        "manager": {
            "password": hashlib.sha256("manager666".encode()).hexdigest(),
            "name": "邓涛",
            "role": "管理",
            "employee_name": "邓涛"
        },
        "worker": {
            "password": hashlib.sha256("worker123".encode()).hexdigest(),
            "name": "李周海",
            "role": "员工",
            "employee_name": "李周海"
        },
        "sushiting": {
            "password": hashlib.sha256("sushiting123".encode()).hexdigest(),
            "name": "苏世婷",
            "role": "客服",
            "employee_name": "苏世婷"
        },
        "liaosimei": {
            "password": hashlib.sha256("liaosimei123".encode()).hexdigest(),
            "name": "廖思美",
            "role": "客服",
            "employee_name": "廖思美"
        }
    }
    default = {
        "users": default_users,  # 持久化的用户密码
        "employee_status": {},  # 考勤状态
        "permission_data": {    # 权限数据
            "processes": [  # 树形结构：美丽湾工厂部/纸箱部 两部门，每部门下工序步骤
                {
                    "dept": "美丽湾工厂部",
                    "steps": [
                        {"id": 1, "name": "客服接单"},
                        {"id": 2, "name": "黄厂打印"},
                        {"id": 3, "name": "审单分单"},
                        {"id": 4, "name": "算料"},
                        {"id": 5, "name": "分纸"},
                        {"id": 6, "name": "啤机(自动平压平)"},
                        {"id": 7, "name": "啤机(机械手)"},
                        {"id": 8, "name": "手啤"},
                        {"id": 9, "name": "印刷"},
                        {"id": 10, "name": "清废"},
                        {"id": 11, "name": "打包发货"}
                    ]
                },
                {
                    "dept": "纸箱部",
                    "steps": [
                        {"id": 1, "name": "客服接单"},
                        {"id": 2, "name": "黄厂打印"},
                        {"id": 3, "name": "审单分单"},
                        {"id": 4, "name": "算料"},
                        {"id": 5, "name": "分纸"},
                        {"id": 6, "name": "印刷"},
                        {"id": 7, "name": "开槽/打角"},
                        {"id": 8, "name": "粘胶/打钉"},
                        {"id": 9, "name": "打包发货"}
                    ]
                }
            ],
            "positions": ["超级管理员", "主管", "客服", "员工", "财务", "业务员"],
            "employee_enabled": {},  # {name: true/false} 员工启用/禁用状态
            "employees": [
                {"name": "戴雅利", "position": "超级管理员"},
                {"name": "邓涛", "position": "主管"},
                {"name": "黄兴", "position": "主管"},
                {"name": "覃海霞", "position": "主管"},
                {"name": "蒋义红", "position": "主管"},
                {"name": "沈齐豪", "position": "主管"},
                {"name": "苏世婷", "position": "客服"},
                {"name": "廖思美", "position": "客服"},
                {"name": "张慧平", "position": "客服"},
                {"name": "陈贝贝", "position": "客服"},
                {"name": "罗怡", "position": "客服"},
                {"name": "周井梅", "position": "客服"},
                {"name": "戴志美", "position": "客服"},
                {"name": "石梅清", "position": "客服"},
                {"name": "张文杰", "position": "客服"},
                {"name": "何水单", "position": "业务员"},
                {"name": "李四军", "position": "员工"},
                {"name": "陈贤聪", "position": "业务员"},
                {"name": "姚斌", "position": "员工"},
                {"name": "隆浪", "position": "财务"},
            ],
            "permissions": {
                "戴雅利": {"首页": True, "订单生产进度": True, "扫码报工": True, "日报表": True, "数据看板": True, "刀模": True, "库存": True, "快麦ERP": True, "员工": True, "权限管理": True, "报价": True},
                "邓涛": {"首页": True, "订单生产进度": True, "扫码报工": True, "日报表": True, "数据看板": True, "刀模": True, "库存": True, "快麦ERP": True, "员工": True, "权限管理": False, "报价": False},
                "李周海": {"首页": True, "订单生产进度": True, "扫码报工": True, "日报表": True, "员工": True, "刀模": False, "库存": False, "快麦ERP": False, "数据看板": False, "权限管理": False, "报价": False},
            }
        }
    }
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 确保所有字段存在
                for key in default:
                    if key not in data:
                        data[key] = default[key]
                # 合并权限数据中的嵌套字段
                for key in default["permission_data"]:
                    if key not in data["permission_data"]:
                        data["permission_data"][key] = default["permission_data"][key]
                # 自动转换旧格式流程（字符串列表→树形）
                processes = data["permission_data"].get("processes", [])
                if processes and isinstance(processes[0], str):
                    data["permission_data"]["processes"] = [
                        {"dept": "美丽湾工厂部", "steps": [{"id": i+1, "name": s} for i, s in enumerate(processes)]}
                    ]
                return data
        except:
            pass
    return default

def save_data(data):
    """保存数据到JSON文件"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

# 初始化数据
persistent_data = load_data()

# 从data.json加载所有用户（覆盖并扩展USERS字典）
_loaded_users = persistent_data.get("users", {})
for uid, uinfo in _loaded_users.items():
    USERS[uid] = {
        "password": uinfo.get("password", ""),
        "name": uinfo.get("name", uid),
        "role": uinfo.get("role", "员工"),
        "employee_name": uinfo.get("employee_name", uinfo.get("name", uid))
    }
_employee_today_status = persistent_data.get("employee_status", {})
_order_extra = persistent_data.get("order_extra", {})
_permission_data = persistent_data.get("permission_data", {})
_resigned_employees = persistent_data.get("resigned_employees", [])  # 离职员工列表[{name, position, group, dept, phone, resigned_time}]

# 将员工状态变更为按日期存储格式（兼容旧格式）
if isinstance(_employee_today_status, dict):
    # 检查是 "date -> name -> status" 还是老格式
    is_old_format = False
    for k, v in _employee_today_status.items():
        if isinstance(v, str):
            is_old_format = True
            break
    if is_old_format:
        today = datetime.date.today().isoformat()
        _employee_today_status = {today: _employee_today_status}

def persist():
    """持久化当前数据到文件"""
    global _employee_today_status, _permission_data, USERS, _resigned_employees
    # 把USERS的密码也存到文件（用户改密码后重启不丢）
    users_data = {}
    for uid, u in USERS.items():
        entry = {
            "password": u["password"],
            "name": u["name"],
            "role": u["role"],
            "employee_name": u["employee_name"]
        }
        if u.get("is_system"):
            entry["is_system"] = True
        users_data[uid] = entry
    data = {
        "users": users_data,
        "employee_status": _employee_today_status,
        "order_extra": _order_extra,
        "permission_data": _permission_data,
        "resigned_employees": _resigned_employees
    }
    save_data(data)

# ==================== 登录API ====================
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    if not username or not password:
        return jsonify({"success": False, "message": "请输入账号和密码"})
    
    user = USERS.get(username)
    if not user:
        return jsonify({"success": False, "message": "账号或密码错误"})
    
    pwd_hash = hashlib.sha256(password.encode()).hexdigest()
    if user['password'] != pwd_hash:
        return jsonify({"success": False, "message": "账号或密码错误"})
    
    # 检查员工是否被禁用
    employee_name = user.get('employee_name', '')
    enabled_map = _permission_data.get("employee_enabled", {})
    # 默认启用，只有明确设为 False 才禁用
    if enabled_map.get(employee_name, True) is False:
        return jsonify({"success": False, "message": "该账号已被禁用，请联系管理员"})
    
    session.permanent = True
    session['username'] = username
    session['user_name'] = user['name']
    session['role'] = user['role']
    session['employee_name'] = user['employee_name']
    session.modified = True

    # 查找用户所属部门
    emp_dept = ''
    for emp in _employees_master_list:
        if emp['name'] == user['employee_name']:
            emp_dept = emp.get('dept', '')
            break

    return jsonify({
        "success": True,
        "message": "登录成功",
        "user": {
            "username": username,
            "name": user['name'],
            "role": user['role'],
            "employee_name": user['employee_name'],
            "dept": emp_dept
        }
    })

@app.route('/api/logout')
def logout():
    session.clear()
    return jsonify({"success": True, "message": "已退出登录"})

@app.route('/api/change_password', methods=['POST'])
def change_password():
    """修改当前登录用户的密码"""
    if 'username' not in session:
        return jsonify({"success": False, "message": "未登录"}), 401
    
    data = request.get_json()
    old_pwd = data.get('old_password', '').strip()
    new_pwd = data.get('new_password', '').strip()
    
    if not old_pwd or not new_pwd:
        return jsonify({"success": False, "message": "请填写旧密码和新密码"})
    
    if len(new_pwd) < 4:
        return jsonify({"success": False, "message": "新密码至少4位"})
    
    username = session['username']
    user = USERS.get(username)
    if not user:
        return jsonify({"success": False, "message": "用户不存在"})
    
    old_hash = hashlib.sha256(old_pwd.encode()).hexdigest()
    if user['password'] != old_hash:
        return jsonify({"success": False, "message": "旧密码错误"})
    
    # 更新密码
    user['password'] = hashlib.sha256(new_pwd.encode()).hexdigest()
    persist()  # 持久化到文件，重启不丢
    return jsonify({"success": True, "message": "密码修改成功"})

@app.route('/api/me')
def get_current_user():
    if 'username' in session:
        user = USERS.get(session['username'])
        if user:
            return jsonify({
                "logged_in": True,
                "user": {
                    "username": session['username'],
                    "name": user['name'],
                    "role": user['role'],
                    "employee_name": user['employee_name']
                }
            })
    return jsonify({"logged_in": False})

# ==================== 首页 - 生产概览 ====================
@app.route('/api/dashboard')
def dashboard():
    date = request.args.get('date', datetime.date.today().strftime('%Y-%m-%d'))
    shop_config = load_shop_config()

    # 从1688订单缓存读取真实数据
    real_orders = []
    try:
        if os.path.exists(ORDERS_CACHE_FILE):
            with open(ORDERS_CACHE_FILE, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            real_orders = cache.get('orders', [])
    except Exception as e:
        print(f'[Dashboard] 读缓存失败: {e}')
        real_orders = []

    # 构建店铺->客服映射（从shop_config读取）
    store_workers = {}
    for sc in shop_config:
        name = sc.get('shop_name', '')
        cs = sc.get('customer_service', '')
        if name and cs:
            store_workers[name] = cs

    # 格式化所有待发货订单（统计卡片用）
    all_orders = []
    for o in real_orders:
        items = o.get('items', [])
        product_parts = []
        total_qty = 0
        for item in items:
            spec = item.get('spec', '') or item.get('name', '')
            qty = item.get('qty', 0)
            total_qty += qty
            if spec:
                product_parts.append(f"{spec}×{qty}")
        product_str = '; '.join(product_parts) if product_parts else '待确认'

        so_id = o.get('so_id', '')
        saved = _order_extra.get(so_id, {})
        shop_name = o.get('shop_name', '亚润')
        all_orders.append({
            "id": so_id,
            "store": shop_name,
            "worker": store_workers.get(shop_name, ""),
            "product": product_str,
            "qty": total_qty,
            "items": items,
            "process": "待发货",
            "status": "待发货",
            "urgent": saved.get("urgent", False),
            "remark": saved.get("remark", "") or o.get('seller_memo', ''),
            "pay_time": o.get('pay_time', '')
        })

    # 统计卡片 = 所有待发货订单的统计
    date_num = date.replace('-', '')

    # 今日订单列表 = 按付款日期过滤当天
    today_orders = [o for o in all_orders if str(o.get('pay_time', '')) == date_num]

    # 统计
    total_all = len(all_orders)           # 总发货（所有订单）
    total_waiting = len([o for o in all_orders if o['status'] == '待发货'])  # 待发货
    urgent_count = len([o for o in all_orders if o.get('urgent')])          # 加急单
    urgent_orders = [o for o in all_orders if o.get('urgent')]
    completed_count = 0                    # 已完成（暂无数据源）

    return jsonify({
        "date": date,
        "summary": {
            "total_orders": total_all,
            "waiting": total_waiting,
            "urgent_orders": urgent_count,
            "completed": completed_count,
        },
        "today_orders": today_orders,
        "urgent_orders": urgent_orders,
    })

# ==================== 订单生产进度 ====================
@app.route('/api/production_orders')
def production_orders():
    """1688待发货订单转为生产进度数据"""
    process_tree = _permission_data.get("processes", [])
    
    def get_flow_for_order(order_type):
        if not process_tree:
            return [{"step": "客服接单", "done": False, "time": "-", "person": ""}]
        is_tree = isinstance(process_tree[0], dict) and 'dept' in process_tree[0]
        if not is_tree:
            return [{"step": s, "done": False, "time": "-", "person": ""} for s in process_tree]
        target_dept = None
        if order_type == '纸箱':
            for d in process_tree:
                if '纸箱' in d.get('dept', ''):
                    target_dept = d; break
        else:
            for d in process_tree:
                if '美丽湾' in d.get('dept', '') or '飞机盒' in d.get('dept', ''):
                    target_dept = d; break
        if not target_dept: target_dept = process_tree[0]
        if not target_dept or not target_dept.get('steps'):
            return [{"step": "客服接单", "done": False, "time": "-", "person": ""}]
        return [{"step": s["name"], "done": False, "time": "-", "person": ""} for s in target_dept.get("steps", [])]
    
    orders_data = []
    try:
        if os.path.exists(ORDERS_CACHE_FILE):
            with open(ORDERS_CACHE_FILE, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            for o in cache.get('orders', []):
                first_item = (o.get('items') or [{}])[0]
                prod_name = first_item.get('name', '')
                order_type = '纸箱' if '纸箱' in prod_name else '飞机盒'
                # 所有规格分行
                specs = []
                for item in (o.get('items') or []):
                    spec = item.get('spec', '') or ''
                    qty = item.get('qty', 0) or 0
                    specs.append({'spec': spec, 'qty': qty})
                total_qty = sum(i.get('qty', 0) for i in (o.get('items') or []))
                addr = o.get('receiver_address', '')
                addr_parts = addr.split() if addr else []
                province = addr_parts[0] if len(addr_parts) > 0 else ''
                city = addr_parts[1] if len(addr_parts) > 1 else ''
                orders_data.append({
                    "inner_id": o.get('so_id', ''),
                    "store": o.get('shop_name', '亚润'),
                    "province": province, "city": city,
                    "specs": specs,
                    "seller_memo": o.get('seller_memo', '') or '',
                    "qty": total_qty, "type": order_type,
                    "flow": get_flow_for_order(order_type)
                })
    except Exception as e:
        print(f'[生产进度] 读取缓存失败: {e}')
    
    # 已完结工序模拟
    for i, order in enumerate(orders_data):
        n = min(i % 4 + 1, len(order["flow"]))
        for j in range(n):
            order["flow"][j]["done"] = True
            order["flow"][j]["time"] = "2026-04-28 09:00"
            order["flow"][j]["person"] = "张慧平"
    
    return jsonify({"orders": orders_data})

# ==================== 扫码报工 ====================
@app.route('/api/scan_report', methods=['POST'])
def scan_report():
    data = request.get_json()
    order_id = data.get('order_id', '')
    step = data.get('step', '')
    worker = data.get('worker', '')
    return jsonify({
        "success": True,
        "message": f"订单 {order_id} 已报工",
        "record": {
            "time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "order_id": order_id,
            "step": step,
            "worker": worker,
            "status": "已完成"
        }
    })

# ==================== 今日报工记录 ====================
@app.route('/api/scan_logs')
def scan_logs():
    return jsonify({
        "logs": [
            {"time": "08:30", "order_id": "JST-20260426-001", "step": "黄厂打印", "worker": "黄兴", "status": "✅"},
            {"time": "08:45", "order_id": "JST-20260426-001", "step": "审单分单", "worker": "覃海霞", "status": "✅"},
            {"time": "09:00", "order_id": "JST-20260426-001", "step": "算料", "worker": "蒋义红", "status": "✅"},
            {"time": "09:20", "order_id": "JST-20260426-002", "step": "黄厂打印", "worker": "黄兴", "status": "✅"},
            {"time": "09:40", "order_id": "JST-20260426-002", "step": "审单分单", "worker": "覃海霞", "status": "✅"},
            {"time": "10:00", "order_id": "JST-20260426-003", "step": "啤机完成", "worker": "蒋义红组", "status": "✅"},
            {"time": "10:15", "order_id": "JST-20260426-002", "step": "算料", "worker": "沈齐豪", "status": "✅"},
            {"time": "14:30", "order_id": "JST-20260426-003", "step": "清废完成", "worker": "清废承包", "status": "✅"},
        ]
    })

# ==================== 日报表 ====================
# 真实报工数据（按你提供的）
DAILY_REPORT_WORKER_DATA = {
    "手啤机组": [
        {"name": "李方国", "total_diemo": 49, "total_pi": 3691, "time": 12},
        {"name": "李周海", "total_diemo": 49, "total_pi": 5592, "time": 12},
        {"name": "唐美章", "total_diemo": 49, "total_pi": 3247, "time": 12},
        {"name": "蒋保平", "total_diemo": 49, "total_pi": 4285, "time": 12},
        {"name": "陈章远", "total_diemo": 50, "total_pi": 4771, "time": 12},
        {"name": "黄振辉", "total_diemo": 67, "total_pi": 3816, "time": 12},
        {"name": "汪成桃", "total_diemo": 29, "total_pi": 5043, "time": 11},
    ],
    "啤机分组": [
        {"name": "易新明", "diemo": 140, "time": 11},
        {"name": "雷善炎", "diemo": 33, "time": 11},
        {"name": "陈海斌", "diemo": 114, "time": 11},
        {"name": "陈奕升", "diemo": 72, "time": 11},
        {"name": "江旭松", "diemo": 63, "time": 11},
    ],
    "刀模组": [
        {"name": "廖金玲", "find_diemo": 302, "time": 12, "remark": ""},
        {"name": "陈勇", "group_diemo": 144, "time": 11, "remark": "没得11单没找42张"},
        {"name": "张吉杰", "remove_diemo": 128, "time": 12, "remark": "没得18单没找42张、查找编号"},
    ],
    "放刀模": [
        {"name": "唐孝定", "time": 12},
    ],
    "机械手组": [
        {"name": "黄恒", "total_diemo": 7, "total_pi": 4808, "time": 11},
        {"name": "李荣晖", "total_diemo": 17, "total_pi": 8643, "time": 11},
    ],
    "平压平组": [
        {"name": "蒋森响", "total_diemo": 24, "total_pi": 11765, "time": 11},
        {"name": "周业福", "total_diemo": 20, "total_pi": 21815, "time": 11},
    ],
    "车间打包组": [
        {"name": "陈桂英", "total_qty": 18443, "total_pieces": 141, "time": 12},
        {"name": "毛良芬", "total_qty": 25249, "total_pieces": 148, "time": 12},
        {"name": "陈辉文", "total_qty": 24483, "total_pieces": 96, "time": 12},
        {"name": "文小梅", "total_qty": 29569, "total_pieces": 106, "time": 12},
        {"name": "帅行朝", "total_qty": 14013, "total_pieces": 89, "time": 12},
        {"name": "黄张华", "total_qty": None, "total_pieces": None, "time": 11},
    ],
    "仓库组": {
        "找货": [
            {"name": "宋小国", "count": 140, "time": 11},
            {"name": "唐忠群", "count": None, "time": None},
        ],
        "打包": [
            {"name": "蒋仁叶", "count": None, "time": None},
            {"name": "罗照权", "count": 152, "time": 11},
        ],
        "放货": [
            {"name": "黄爱小", "qty": 29540, "time": 12, "remark": "打包71包、找货50单"},
        ],
        "打样兼配货": [
            {"name": "龙雪兰", "size": 79, "time": 12, "remark": "粘二合一，耗时5小时"},
        ],
    },
    "印刷组": [
        {"name": "李双", "diemo": 11, "qty": 10130, "time": 11},
    ],
    "扣底盒组": [
        {"name": "蒋军林", "size": 12, "qty": None, "time": 11},
        {"name": "宁哈姝", "size": 15, "qty": 10630, "time": 11},
        {"name": "黄华", "task": "打包", "size": "打包", "time": 11},
    ],
    "纸箱分纸组": [
        {"name": "陈伟", "size": 65, "qty": None, "time": 7},
        {"name": "陈陶", "size": 66, "qty": None, "time": 11},
        {"name": "周石国", "size": 72, "qty": None, "time": 11},
    ],
    "纸箱开槽组": [
        {"name": "杨家忠", "size": 41, "qty": 10419, "time": 11},
        {"name": "沈奇严", "size": 75, "qty": 3098, "time": 11},
        {"name": "姚建桥", "size": 62, "qty": 6308, "time": 11},
    ],
    "纸箱粘胶组": [
        {"name": "戴西华", "size": 23, "qty": 4995, "time": 11},
        {"name": "魏小王", "size": 36, "qty": 8569, "time": 11},
        {"name": "黄芳", "size": 31, "qty": 1666, "time": 11},
        {"name": "于天发", "size": 41, "qty": 1878, "time": 11},
    ],
}

@app.route('/api/daily_report')
def daily_report():
    date = request.args.get('date', datetime.date.today().strftime('%Y-%m-%d'))
    # 获取考勤状态
    today = datetime.date.today().isoformat()
    emp_statuses = _employee_today_status.get(today, {})
    
    # 构建员工报工统计
    worker_stats = []
    for group_name, members in DAILY_REPORT_WORKER_DATA.items():
        if isinstance(members, list):
            for m in members:
                worker_stats.append({
                    "name": m.get("name", ""),
                    "dept": m.get("dept", "美丽湾工厂部"),
                    "position": group_name,
                    "group": group_name,
                    "data": m,
                    "status": emp_statuses.get(m.get("name", ""), "出勤")
                })
        elif isinstance(members, dict):
            for sub_group, sub_members in members.items():
                for m in sub_members:
                    worker_stats.append({
                        "name": m.get("name", ""),
                        "dept": m.get("dept", "美丽湾工厂部"),
                        "position": f"{group_name}-{sub_group}",
                        "group": f"{group_name}-{sub_group}",
                        "data": m,
                        "status": emp_statuses.get(m.get("name", ""), "出勤")
                    })
    
    return jsonify({
        "date": date,
        "summary": {
            "total_orders": 45,
            "completed_orders": 14,
            "output_qty": 12500,
            "defect_rate": "1.2%",
        },
        "comparison": [
            {"name": "总单数", "today": "45", "yesterday": "38", "change": "+18.4%"},
            {"name": "完成数", "today": "14", "yesterday": "11", "change": "+27.3%"},
            {"name": "总产出", "today": "12,500", "yesterday": "10,800", "change": "+15.7%"},
            {"name": "不良率", "today": "1.2%", "yesterday": "1.5%", "change": "-0.3%"},
        ],
        "production_lines": [
            {"line": "飞机盒线-自动平压平", "output": 5800, "status": "正常"},
            {"line": "飞机盒线-机械手", "output": 3200, "status": "正常"},
            {"line": "飞机盒线-手啤", "output": 1500, "status": "正常"},
            {"line": "纸箱线", "output": 2000, "status": "正常"},
        ],
        "done_orders": [
            {"id": "JST-20260425-005", "product": "飞机盒20*15*10（现货）", "qty": 800, "last_step": "打包发货", "done_time": "16:00"},
            {"id": "JST-20260425-003", "product": "飞机盒25*15*10", "qty": 300, "last_step": "打包发货", "done_time": "15:30"},
            {"id": "JST-20260426-001", "product": "飞机盒30*20*15", "qty": 200, "last_step": "清废", "done_time": "14:20"},
        ],
        # 更新为真实报工数据
        "worker_stats": worker_stats,
        "worker_data": DAILY_REPORT_WORKER_DATA  # 原始分组数据
    })

# ==================== 数据看板 ====================
@app.route('/api/databoard')
def databoard():
    range_type = request.args.get('range', 'week')
    # 模拟不同时间范围的数据
    if range_type == 'month':
        trend = [
            {"date": "04-01", "output": 1800},{"date": "04-03", "output": 2100},{"date": "04-05", "output": 1950},
            {"date": "04-07", "output": 2400},{"date": "04-09", "output": 2250},{"date": "04-11", "output": 2600},
            {"date": "04-13", "output": 2500},{"date": "04-15", "output": 2800},{"date": "04-17", "output": 2700},
            {"date": "04-19", "output": 2900},{"date": "04-21", "output": 3100},{"date": "04-23", "output": 3050},
            {"date": "04-25", "output": 3200},{"date": "04-26", "output": 3350},
        ]
    elif range_type == 'quarter':
        trend = [
            {"date": "02月", "output": 42000},{"date": "03月", "output": 48000},{"date": "04月", "output": 52000},
        ]
    else:
        trend = [
            {"date": "04-21", "output": 1800},{"date": "04-22", "output": 2100},{"date": "04-23", "output": 1950},
            {"date": "04-24", "output": 2400},{"date": "04-25", "output": 2250},{"date": "04-26", "output": 2500},
        ]

    return jsonify({
        "stats": {
            "total_output": 12500,
            "total_orders": 45,
            "completed": 14,
            "in_production": 28,
            "avg_daily": 2080,
            "on_time_rate": "94.5%",
            "defect_rate": "1.2%",
            "urgent_count": 3,
        },
        "trend": trend,
        "store_distribution": [
            {"name": "友尚旗舰店", "count": 12, "pct": 27},
            {"name": "亚润跨境", "count": 8, "pct": 18},
            {"name": "三羊现货", "count": 7, "pct": 16},
            {"name": "正方形定制", "count": 5, "pct": 11},
            {"name": "其他店铺", "count": 13, "pct": 28},
        ],
        "process_load": [
            {"name": "审单", "current": 5, "capacity": 10, "pct": 50},
            {"name": "算料", "current": 8, "capacity": 10, "pct": 80},
            {"name": "啤机", "current": 12, "capacity": 15, "pct": 80},
            {"name": "清废", "current": 6, "capacity": 10, "pct": 60},
            {"name": "打包发货", "current": 9, "capacity": 12, "pct": 75},
        ],
        "product_type": [
            {"name": "飞机盒(固定刀模)", "count": 15, "pct": 33},
            {"name": "飞机盒(组合刀模)", "count": 8, "pct": 18},
            {"name": "飞机盒(手啤)", "count": 7, "pct": 16},
            {"name": "纸箱", "count": 10, "pct": 22},
            {"name": "现货直发", "count": 5, "pct": 11},
        ],
        "hourly_output": [
            {"hour": "08", "val": 120},{"hour": "09", "val": 350},{"hour": "10", "val": 580},
            {"hour": "11", "val": 720},{"hour": "12", "val": 800},{"hour": "13", "val": 650},
            {"hour": "14", "val": 920},{"hour": "15", "val": 1100},{"hour": "16", "val": 1250},
            {"hour": "17", "val": 1350},{"hour": "18", "val": 1100},{"hour": "19", "val": 850},
        ],
        "worker_productivity": [
            {"name": "蒋义红组", "output": 4500, "target": 5000, "pct": 90},
            {"name": "沈齐豪组", "output": 3500, "target": 4000, "pct": 88},
            {"name": "清废承包", "output": 2800, "target": 3000, "pct": 93},
            {"name": "仓库组", "output": 1700, "target": 2000, "pct": 85},
        ]
    })

def _orders_cache_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "orders_cache.json")


def _find_cached_order(query):
    query = (query or "").strip()
    if not query:
        return None
    path = _orders_cache_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            cache = json.load(f)
    except Exception:
        return None
    q = query.lower()
    for o in cache.get("orders", []):
        so_id = str(o.get("so_id", "") or "")
        tid = str(o.get("tid", "") or o.get("platform_tid", "") or "")
        if query == so_id or query == tid or q in so_id.lower() or (tid and q in tid.lower()):
            return o
    return None


def _order_detail_from_cache(o):
    items = o.get("items") or []
    first = items[0] if items else {}
    product = first.get("name", "") or first.get("spec", "") or "?"
    if len(items) > 1:
        product += f" 等{len(items)}种"
    qty = sum(int(i.get("qty", 0) or 0) for i in items)
    amount = o.get("payment") or o.get("pay_amount") or o.get("total_fee") or 0
    return {
        "order_id": o.get("so_id", ""),
        "store": o.get("shop_name", ""),
        "customer": o.get("receiver_name", "") or o.get("buyer_nick", "") or "",
        "product": product,
        "qty": qty,
        "amount": amount,
        "order_date": (o.get("created") or o.get("pay_time") or "")[:10],
        "delivery_date": (o.get("plan_delivery_date") or o.get("consign_time") or "")[:10],
        "address": o.get("receiver_address", "") or "",
        "logistics": o.get("logistics_company", "") or o.get("express", "") or "",
    }


def _production_status_from_flow(flow):
    flow = flow or []
    done = [s for s in flow if s.get("done")]
    total = len(flow) or 1
    progress = int(len(done) * 100 / total)
    current = "-"
    for s in flow:
        if not s.get("done"):
            current = s.get("step") or s.get("name", "-")
            break
    else:
        if flow:
            current = flow[-1].get("step") or flow[-1].get("name", "已完成")
    status = "已完成" if progress >= 100 and flow else ("生产中" if done else "待处理")
    steps = [
        {"name": s.get("step") or s.get("name", ""), "done": bool(s.get("done")), "time": s.get("time", "-")}
        for s in flow
    ]
    return {"status": status, "current_process": current, "diemold": "", "progress": progress, "steps": steps}


# ==================== 搜索订单 ====================
@app.route('/api/search_order')
def search_order():
    """扫码/输入单号：从 orders_cache.json 查订单（快麦+1688）。"""
    query = (request.args.get('q') or '').strip()
    if not query:
        return jsonify({"found": False, "message": "请输入单号"})
    o = _find_cached_order(query)
    if not o:
        return jsonify({"found": False, "message": "未找到该订单"})
    so_id = o.get("so_id", "")
    extra = _order_extra.get(so_id, {})
    prod_resp = production_orders().get_json()
    prod = next((x for x in prod_resp.get("orders", []) if x.get("inner_id") == so_id), None)
    flow = (prod or {}).get("flow") or []
    detail = _order_detail_from_cache(o)
    return jsonify({
        "found": True,
        "order_id": so_id,
        "urgent": bool(extra.get("urgent")),
        "production_status": _production_status_from_flow(flow),
        "order_detail": detail,
        "jst_detail": detail,
    })

# ==================== 生产进度 ====================
@app.route('/api/production_timeline')
def production_timeline():
    return jsonify({
        "stages": [
            {"id": 1, "name": "客服接单", "color": "#1677ff", "icon": "📞"},
            {"id": 2, "name": "黄厂打印", "color": "#52c41a", "icon": "🖨️"},
            {"id": 3, "name": "审单分单", "color": "#faad14", "icon": "📋"},
            {"id": 4, "name": "算料", "color": "#722ed1", "icon": "📐"},
            {"id": 5, "name": "生产制作", "color": "#1677ff", "icon": "🏭"},
            {"id": 6, "name": "清废", "color": "#13c2c2", "icon": "🧹"},
            {"id": 7, "name": "打包发货", "color": "#52c41a", "icon": "🚚"},
        ]
    })

# ==================== 员工信息（增强版，带手机号和厂区） ====================
# 全局员工列表（方便增删改API共享）
_employees_master_list = [
    # ===== 洋坑塘运营部（电商运营中心） =====
    {"name": "戴雅利", "position": "总负责人", "group": "管理层", "dept": "洋坑塘运营部", "phone": "13800138001"},
    {"name": "苏世婷", "position": "阿里客服主管", "group": "客服组", "dept": "洋坑塘运营部", "phone": "13800138002"},
    {"name": "廖思美", "position": "淘天客服主管", "group": "客服组", "dept": "洋坑塘运营部", "phone": "13800138003"},
    {"name": "何水单", "position": "业务员", "group": "业务组", "dept": "洋坑塘运营部", "phone": "13800138004"},
    {"name": "李四军", "position": "美工", "group": "业务组", "dept": "洋坑塘运营部", "phone": "13800138005"},
    {"name": "陈贤聪", "position": "抖音/微信/珍珠棉业务", "group": "业务组", "dept": "洋坑塘运营部", "phone": "13800138006"},
    {"name": "张慧平", "position": "友尚旗舰店运营", "group": "客服组", "dept": "洋坑塘运营部", "phone": "13800138007"},
    {"name": "陈贝贝", "position": "亚润跨境运营", "group": "客服组", "dept": "洋坑塘运营部", "phone": "13800138008"},
    {"name": "罗怡", "position": "三羊现货运营", "group": "客服组", "dept": "洋坑塘运营部", "phone": "13800138009"},
    {"name": "周井梅", "position": "正方形/大鱼运营", "group": "客服组", "dept": "洋坑塘运营部", "phone": "13800138010"},
    {"name": "戴志美", "position": "友尚/新鑫星运营", "group": "客服组", "dept": "洋坑塘运营部", "phone": "13800138011"},
    {"name": "石梅清", "position": "止合/扣底盒运营", "group": "客服组", "dept": "洋坑塘运营部", "phone": "13800138012"},
    {"name": "张文杰", "position": "小批量/品牌店运营", "group": "客服组", "dept": "洋坑塘运营部", "phone": "13800138013"},
    {"name": "姚斌", "position": "采购/跟单/机动", "group": "综合组", "dept": "洋坑塘运营部", "phone": "13800138014"},
    # ===== 美丽湾工厂部-管理层 =====
    {"name": "邓涛", "position": "生产总监", "group": "管理层", "dept": "美丽湾工厂部", "phone": "13800138015"},
    {"name": "黄兴", "position": "行政总监", "group": "管理层", "dept": "美丽湾工厂部", "phone": "13800138016"},
    {"name": "隆浪", "position": "财务总监", "group": "管理层", "dept": "美丽湾工厂部", "phone": "13800138017"},
    {"name": "蒋义红", "position": "飞机盒主管", "group": "管理层", "dept": "美丽湾工厂部", "phone": "13800138018"},
    {"name": "沈齐豪", "position": "纸箱主管", "group": "管理层", "dept": "美丽湾工厂部", "phone": "13800138019"},
    {"name": "覃海霞", "position": "综合主管", "group": "管理层", "dept": "美丽湾工厂部", "phone": "13800138020"},
    # ===== 美丽湾工厂部-手啤机组 =====
    {"name": "李方国", "position": "手啤机-啤工", "group": "手啤机组", "dept": "美丽湾工厂部", "phone": "13800138021"},
    {"name": "李周海", "position": "手啤机-啤工", "group": "手啤机组", "dept": "美丽湾工厂部", "phone": "13800138022"},
    {"name": "唐美章", "position": "手啤机-啤工", "group": "手啤机组", "dept": "美丽湾工厂部", "phone": "13800138023"},
    {"name": "蒋保平", "position": "手啤机-啤工", "group": "手啤机组", "dept": "美丽湾工厂部", "phone": "13800138024"},
    {"name": "陈章远", "position": "手啤机-啤工", "group": "手啤机组", "dept": "美丽湾工厂部", "phone": "13800138025"},
    {"name": "黄振辉", "position": "手啤机-啤工", "group": "手啤机组", "dept": "美丽湾工厂部", "phone": "13800138026"},
    {"name": "汪成桃", "position": "手啤机-啤工", "group": "手啤机组", "dept": "美丽湾工厂部", "phone": "13800138027"},
    # ===== 美丽湾工厂部-啤机分组 =====
    {"name": "易新明", "position": "啤机分纸", "group": "啤机分组", "dept": "美丽湾工厂部", "phone": "13800138028"},
    {"name": "雷善炎", "position": "啤机分纸", "group": "啤机分组", "dept": "美丽湾工厂部", "phone": "13800138029"},
    {"name": "陈海斌", "position": "啤机分纸", "group": "啤机分组", "dept": "美丽湾工厂部", "phone": "13800138030"},
    {"name": "陈奕升", "position": "啤机分纸", "group": "啤机分组", "dept": "美丽湾工厂部", "phone": "13800138031"},
    {"name": "江旭松", "position": "啤机分纸", "group": "啤机分组", "dept": "美丽湾工厂部", "phone": "13800138032"},
    # ===== 美丽湾工厂部-刀模组 =====
    {"name": "廖金玲", "position": "刀模-找刀模", "group": "刀模组", "dept": "美丽湾工厂部", "phone": "13800138033"},
    {"name": "陈勇", "position": "刀模-组刀模", "group": "刀模组", "dept": "美丽湾工厂部", "phone": "13800138034"},
    {"name": "张吉杰", "position": "刀模-拆刀模", "group": "刀模组", "dept": "美丽湾工厂部", "phone": "13800138035"},
    {"name": "唐孝定", "position": "放刀模", "group": "刀模组", "dept": "美丽湾工厂部", "phone": "13800138036"},
    # ===== 美丽湾工厂部-机械手组 =====
    {"name": "黄恒", "position": "机械手啤工", "group": "机械手组", "dept": "美丽湾工厂部", "phone": "13800138037"},
    {"name": "李荣晖", "position": "机械手啤工", "group": "机械手组", "dept": "美丽湾工厂部", "phone": "13800138038"},
    # ===== 美丽湾工厂部-平压平组 =====
    {"name": "蒋森响", "position": "平压平啤工", "group": "平压平组", "dept": "美丽湾工厂部", "phone": "13800138039"},
    {"name": "周业福", "position": "平压平啤工", "group": "平压平组", "dept": "美丽湾工厂部", "phone": "13800138040"},
    # ===== 美丽湾工厂部-车间打包组 =====
    {"name": "陈桂英", "position": "车间打包", "group": "车间打包组", "dept": "美丽湾工厂部", "phone": "13800138041"},
    {"name": "毛良芬", "position": "车间打包", "group": "车间打包组", "dept": "美丽湾工厂部", "phone": "13800138042"},
    {"name": "陈辉文", "position": "车间打包", "group": "车间打包组", "dept": "美丽湾工厂部", "phone": "13800138043"},
    {"name": "文小梅", "position": "车间打包", "group": "车间打包组", "dept": "美丽湾工厂部", "phone": "13800138044"},
    {"name": "帅行朝", "position": "车间打包", "group": "车间打包组", "dept": "美丽湾工厂部", "phone": "13800138045"},
    {"name": "黄张华", "position": "车间打包", "group": "车间打包组", "dept": "美丽湾工厂部", "phone": "13800138046"},
    # ===== 美丽湾工厂部-仓库组 =====
    {"name": "宋小国", "position": "仓库-找货", "group": "仓库组", "dept": "美丽湾工厂部", "phone": "13800138047"},
    {"name": "唐忠群", "position": "仓库-找货", "group": "仓库组", "dept": "美丽湾工厂部", "phone": "13800138048"},
    {"name": "蒋仁叶", "position": "仓库-打包", "group": "仓库组", "dept": "美丽湾工厂部", "phone": "13800138049"},
    {"name": "罗照权", "position": "仓库-打包", "group": "仓库组", "dept": "美丽湾工厂部", "phone": "13800138050"},
    {"name": "黄爱小", "position": "仓库-放货", "group": "仓库组", "dept": "美丽湾工厂部", "phone": "13800138051"},
    {"name": "龙雪兰", "position": "仓库-打样兼配货", "group": "仓库组", "dept": "美丽湾工厂部", "phone": "13800138052"},
    # ===== 美丽湾工厂部-印刷组 =====
    {"name": "李双", "position": "印刷", "group": "印刷组", "dept": "美丽湾工厂部", "phone": "13800138053"},
    # ===== 美丽湾工厂部-扣底盒 =====
    {"name": "蒋军林", "position": "扣底盒", "group": "扣底盒组", "dept": "美丽湾工厂部", "phone": "13800138054"},
    {"name": "宁哈姝", "position": "扣底盒", "group": "扣底盒组", "dept": "美丽湾工厂部", "phone": "13800138055"},
    {"name": "黄华", "position": "扣底盒-打包", "group": "扣底盒组", "dept": "美丽湾工厂部", "phone": "13800138056"},
    # ===== 美丽湾工厂部-纸箱部(分纸) =====
    {"name": "陈伟", "position": "纸箱-分纸", "group": "纸箱分纸组", "dept": "美丽湾工厂部", "phone": "13800138057"},
    {"name": "陈陶", "position": "纸箱-分纸", "group": "纸箱分纸组", "dept": "美丽湾工厂部", "phone": "13800138058"},
    {"name": "周石国", "position": "纸箱-分纸", "group": "纸箱分纸组", "dept": "美丽湾工厂部", "phone": "13800138059"},
    # ===== 美丽湾工厂部-纸箱部(开槽) =====
    {"name": "杨家忠", "position": "纸箱-开槽", "group": "纸箱开槽组", "dept": "美丽湾工厂部", "phone": "13800138060"},
    {"name": "沈奇严", "position": "纸箱-开槽", "group": "纸箱开槽组", "dept": "美丽湾工厂部", "phone": "13800138061"},
    {"name": "姚建桥", "position": "纸箱-开槽", "group": "纸箱开槽组", "dept": "美丽湾工厂部", "phone": "13800138062"},
    # ===== 美丽湾工厂部-纸箱部(粘胶) =====
    {"name": "戴西华", "position": "纸箱-粘胶", "group": "纸箱粘胶组", "dept": "美丽湾工厂部", "phone": "13800138063"},
    {"name": "魏小王", "position": "纸箱-粘胶", "group": "纸箱粘胶组", "dept": "美丽湾工厂部", "phone": "13800138064"},
    {"name": "黄芳", "position": "纸箱-粘胶", "group": "纸箱粘胶组", "dept": "美丽湾工厂部", "phone": "13800138065"},
    {"name": "于天发", "position": "纸箱-粘胶/打角", "group": "纸箱粘胶组", "dept": "美丽湾工厂部", "phone": "13800138066"},
]

@app.route('/api/employees')
def employees():
    # 过滤掉系统账号的员工（admin是系统账号，对应的员工名不出现在列表）
    # 规则：员工的名称如果被某个 is_system 用户引用，且没有被非system用户引用，则过滤
    system_emp_names = set()
    real_emp_names = set()
    for u in USERS.values():
        emp_name = u.get("employee_name", "")
        if u.get("is_system"):
            system_emp_names.add(emp_name)
        else:
            real_emp_names.add(emp_name)
    # 只过滤掉纯system用户的员工名
    exclude_names = system_emp_names - real_emp_names
    filtered = [e for e in _employees_master_list if e["name"] not in exclude_names]
    return jsonify({"employees": filtered})


# ==================== 员工编辑API ====================
@app.route('/api/employee/update', methods=['POST'])
def update_employee():
    """编辑员工信息（admin权限）"""
    if 'username' not in session:
        return jsonify({"success": False, "message": "未登录"}), 401
    user = USERS.get(session['username'])
    if not user or user['role'] != '超级管理员':
        return jsonify({"success": False, "message": "仅管理员可编辑员工"}), 403
    
    data = request.get_json()
    old_name = data.get('old_name', '')
    new_name = data.get('name', '')
    position = data.get('position', '')
    group = data.get('group', '')
    phone = data.get('phone', '')
    dept = data.get('dept', '')
    
    if not old_name or not new_name:
        return jsonify({"success": False, "message": "请提供员工姓名"})
    
    # 更新雇员列表
    for emp in _employees_master_list:
        if emp['name'] == old_name:
            emp['name'] = new_name
            if position: emp['position'] = position
            if group: emp['group'] = group
            if phone: emp['phone'] = phone
            if dept: emp['dept'] = dept
            return jsonify({"success": True, "message": f"员工 {old_name} 信息已更新"})
    
    return jsonify({"success": False, "message": f"未找到员工 {old_name}"})

@app.route('/api/employee/add', methods=['POST'])
def add_employee():
    """添加新员工（admin权限）——自动生成登录账号和部门默认权限"""
    if 'username' not in session:
        return jsonify({"success": False, "message": "未登录"}), 401
    user = USERS.get(session['username'])
    if not user or user['role'] != '超级管理员':
        return jsonify({"success": False, "message": "仅管理员可添加员工"}), 403
    
    data = request.get_json()
    name = data.get('name', '').strip()
    position = data.get('position', '').strip()
    group = data.get('group', '').strip()
    phone = data.get('phone', '').strip()
    dept = data.get('dept', '美丽湾工厂部').strip()
    
    if not name:
        return jsonify({"success": False, "message": "请填写员工姓名"})
    
    # 检查是否已存在
    for emp in _employees_master_list:
        if emp['name'] == name:
            return jsonify({"success": False, "message": f"员工 {name} 已存在"})
    
    _employees_master_list.append({
        "name": name,
        "position": position or "员工",
        "group": group or "其他",
        "dept": dept,
        "phone": phone or ""
    })
    
    # === 自动生成登录账号 ===
    # 姓名拼音转小写+去空格
    pinyin_parts = lazy_pinyin(name)
    raw_username = ''.join(pinyin_parts).lower().replace(' ', '')
    # 去掉非字母数字字符（某些特殊汉字拼音可能含标点）
    raw_username = re.sub(r'[^a-z0-9]', '', raw_username)
    
    # 如果用户名已存在则加数字后缀
    username = raw_username
    suffix = 1
    while username in USERS:
        suffix += 1
        username = f"{raw_username}{suffix}"
    
    # 默认密码 = 姓名拼音 + "123"
    default_pwd = f"{username}123"
    pwd_hash = hashlib.sha256(default_pwd.encode()).hexdigest()
    
    # 根据部门确定默认角色
    if dept == '洋坑塘运营部':
        default_role = '客服'
    else:
        default_role = '员工'
    
    # 注册到USERS
    USERS[username] = {
        "password": pwd_hash,
        "name": name,
        "role": default_role,
        "employee_name": name
    }
    
    # === 根据部门给默认权限 ===
    perms = _permission_data.setdefault("permissions", {})
    if name not in perms:
        perms[name] = {}
    
    if dept == '洋坑塘运营部':
        # 洋坑塘默认：客服权限——查单/库存，不涉及生产
        default_funcs = {
            '快麦ERP': True, '订单': True, '订单备注': True, '库存': True,
            '刀模': True, '报价': True, '智能报价': True,
            '刀模库': True, '原材料': True, '员工': True,
            '首页-加急单': True
        }
    else:
        # 美丽湾默认：员工权限——报工、考勤、查看
        default_funcs = {
            '员工': True, '首页-加急单': True
        }
    
    for func, val in default_funcs.items():
        perms[name][func] = val
    
    # 保存到data.json
    persist()
    
    return jsonify({
        "success": True,
        "message": f"员工 {name} 已添加，登录账号: {username}，默认密码: {default_pwd}，部门: {dept}",
        "username": username,
        "default_password": default_pwd,
        "role": default_role
    })

@app.route('/api/employee/delete', methods=['POST'])
def delete_employee():
    """删除员工（admin权限）"""
    if 'username' not in session:
        return jsonify({"success": False, "message": "未登录"}), 401
    user = USERS.get(session['username'])
    if not user or user['role'] != '超级管理员':
        return jsonify({"success": False, "message": "仅管理员可删除员工"}), 403
    
    data = request.get_json()
    name = data.get('name', '')
    
    for i, emp in enumerate(_employees_master_list):
        if emp['name'] == name:
            _employees_master_list.pop(i)
            return jsonify({"success": True, "message": f"员工 {name} 已删除"})
    
    return jsonify({"success": False, "message": f"未找到员工 {name}"})


# ==================== 员工离职/恢复 ====================
@app.route('/api/employee/deactivate', methods=['POST'])
def deactivate_employee():
    """标记员工为离职 - 核心管理(邓涛/黄兴/隆浪)可操作"""
    if 'username' not in session:
        return jsonify({"success": False, "message": "未登录"}), 401
    user = USERS.get(session['username'])
    if not user or user['role'] not in ['超级管理员', '管理']:
        return jsonify({"success": False, "message": "仅管理员可操作"}), 403
    
    global _resigned_employees
    data = request.get_json()
    name = data.get('name', '')
    
    for i, emp in enumerate(_employees_master_list):
        if emp['name'] == name:
            # 移到离职列表
            _resigned_employees.append({
                "name": emp['name'],
                "position": emp.get('position', ''),
                "group": emp.get('group', ''),
                "dept": emp.get('dept', ''),
                "phone": emp.get('phone', ''),
                "resigned_time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
                "operator": user.get('name', '')
            })
            _employees_master_list.pop(i)
            persist()
            return jsonify({"success": True, "message": f"员工 {name} 已离职"})
    
    return jsonify({"success": False, "message": f"未找到员工 {name}"})

@app.route('/api/employee/restore', methods=['POST'])
def restore_employee():
    """恢复离职员工 - 仅超级管理员"""
    if 'username' not in session:
        return jsonify({"success": False, "message": "未登录"}), 401
    user = USERS.get(session['username'])
    if not user or user['role'] != '超级管理员':
        return jsonify({"success": False, "message": "仅超级管理员可恢复"}), 403
    
    global _resigned_employees
    data = request.get_json()
    name = data.get('name', '')
    
    for i, emp in enumerate(_resigned_employees):
        if emp['name'] == name:
            # 恢复到员工列表
            _employees_master_list.append({
                "name": emp['name'],
                "position": emp.get('position', ''),
                "group": emp.get('group', ''),
                "dept": emp.get('dept', ''),
                "phone": emp.get('phone', '')
            })
            _resigned_employees.pop(i)
            persist()
            return jsonify({"success": True, "message": f"员工 {name} 已恢复"})
    
    return jsonify({"success": False, "message": f"未找到离职员工 {name}"})

@app.route('/api/employee/resigned')
def list_resigned():
    """获取离职员工列表"""
    return jsonify({"employees": _resigned_employees})

@app.route('/api/employee/delete_resigned', methods=['POST'])
def delete_resigned():
    """彻底删除离职员工记录 - 仅超级管理员"""
    if 'username' not in session:
        return jsonify({"success": False, "message": "未登录"}), 401
    user = USERS.get(session['username'])
    if not user or user['role'] != '超级管理员':
        return jsonify({"success": False, "message": "仅超级管理员可操作"}), 403
    
    global _resigned_employees
    data = request.get_json()
    name = data.get('name', '')
    
    for i, emp in enumerate(_resigned_employees):
        if emp['name'] == name:
            _resigned_employees.pop(i)
            persist()
            return jsonify({"success": True, "message": f"已彻底删除 {name} 的记录"})
    
    return jsonify({"success": False, "message": f"未找到离职员工 {name}"})


# ==================== 员工今日状态 ====================
# 模拟数据：每天重置
_employee_today_status = {}

@app.route('/api/employee/status', methods=['GET'])
def get_employee_status():
    global _employee_today_status
    today = datetime.date.today().isoformat()
    if today not in _employee_today_status:
        _employee_today_status[today] = {}
    return jsonify({
        "date": today,
        "statuses": _employee_today_status[today]
    })

@app.route('/api/employee/status', methods=['POST'])
def update_employee_status():
    """更新员工考勤状态 - 员工只能改自己的，管理可改所有人"""
    if 'username' not in session:
        return jsonify({"error": "未登录", "code": 401}), 401
    user = USERS.get(session['username'])
    if not user:
        return jsonify({"error": "无权限", "code": 403}), 403
    
    data = request.get_json()
    name = data.get('name', '')
    status = data.get('status', '出勤')
    
    # 员工只能改自己的
    if user['role'] == '员工':
        if name != user['employee_name']:
            return jsonify({"error": "无权限：仅可修改自己的考勤", "code": 403}), 403

    global _employee_today_status
    today = datetime.date.today().isoformat()
    if today not in _employee_today_status:
        _employee_today_status[today] = {}
    if name:
        _employee_today_status[today][name] = status
        persist()  # 持久化到文件
    return jsonify({
        "date": today,
        "name": name,
        "status": status,
        "success": True
    })

# ==================== 订单备注和加急API ====================
@app.route('/api/order/remark', methods=['POST'])
def order_remark():
    """设置订单备注 - 仅 超级管理员/管理/客服 可操作"""
    if 'username' not in session:
        return jsonify({"error": "未登录", "code": 401}), 401
    user = USERS.get(session['username'])
    if not user or user['role'] == '员工':
        return jsonify({"error": "无权限", "code": 403}), 403
    global _order_extra
    data = request.get_json()
    oid = data.get('order_id', '')
    remark = data.get('remark', '')
    if oid:
        if oid not in _order_extra:
            _order_extra[oid] = {}
        _order_extra[oid]['remark'] = remark
        persist()
    return jsonify({"success": True, "order_id": oid, "remark": remark})

@app.route('/api/order/urgent', methods=['POST'])
def order_urgent():
    """切换加急状态 - 仅 超级管理员/管理/客服 可操作"""
    if 'username' not in session:
        return jsonify({"error": "未登录", "code": 401}), 401
    user = USERS.get(session['username'])
    if not user or user['role'] == '员工':
        return jsonify({"error": "无权限", "code": 403}), 403
    global _order_extra
    data = request.get_json()
    oid = data.get('order_id', '')
    urgent = data.get('urgent', False)
    if oid:
        if oid not in _order_extra:
            _order_extra[oid] = {}
        _order_extra[oid]['urgent'] = urgent
        persist()
    return jsonify({"success": True, "order_id": oid, "urgent": urgent})

# ==================== 导出今日考勤CSV ====================
@app.route('/api/employee/export')
def export_attendance():
    global _employee_today_status
    date_str = request.args.get('date', datetime.date.today().isoformat())
    today = date_str
    # 如果请求的日期没有数据，初始化为空
    if today not in _employee_today_status:
        _employee_today_status[today] = {}

    _employees_master_list = [
        # ===== 洋坑塘运营部 =====
        {"name": "戴雅利", "position": "总负责人", "group": "管理层", "dept": "洋坑塘运营部", "phone": "13800138001"},
        {"name": "苏世婷", "position": "阿里客服主管", "group": "客服组", "dept": "洋坑塘运营部", "phone": "13800138002"},
        {"name": "廖思美", "position": "淘天客服主管", "group": "客服组", "dept": "洋坑塘运营部", "phone": "13800138003"},
        {"name": "何水单", "position": "业务员", "group": "业务组", "dept": "洋坑塘运营部", "phone": "13800138004"},
        {"name": "李四军", "position": "美工", "group": "业务组", "dept": "洋坑塘运营部", "phone": "13800138005"},
        {"name": "陈贤聪", "position": "抖音/微信/珍珠棉业务", "group": "业务组", "dept": "洋坑塘运营部", "phone": "13800138006"},
        {"name": "张慧平", "position": "友尚旗舰店运营", "group": "客服组", "dept": "洋坑塘运营部", "phone": "13800138007"},
        {"name": "陈贝贝", "position": "亚润跨境运营", "group": "客服组", "dept": "洋坑塘运营部", "phone": "13800138008"},
        {"name": "罗怡", "position": "三羊现货运营", "group": "客服组", "dept": "洋坑塘运营部", "phone": "13800138009"},
        {"name": "周井梅", "position": "正方形/大鱼运营", "group": "客服组", "dept": "洋坑塘运营部", "phone": "13800138010"},
        {"name": "戴志美", "position": "友尚/新鑫星运营", "group": "客服组", "dept": "洋坑塘运营部", "phone": "13800138011"},
        {"name": "石梅清", "position": "止合/扣底盒运营", "group": "客服组", "dept": "洋坑塘运营部", "phone": "13800138012"},
        {"name": "张文杰", "position": "小批量/品牌店运营", "group": "客服组", "dept": "洋坑塘运营部", "phone": "13800138013"},
        {"name": "姚斌", "position": "采购/跟单/机动", "group": "综合组", "dept": "洋坑塘运营部", "phone": "13800138014"},
        # ===== 美丽湾工厂部-管理层 =====
        {"name": "邓涛", "position": "生产总监", "group": "管理层", "dept": "美丽湾工厂部", "phone": "13800138015"},
        {"name": "黄兴", "position": "行政总监", "group": "管理层", "dept": "美丽湾工厂部", "phone": "13800138016"},
        {"name": "隆浪", "position": "财务总监", "group": "管理层", "dept": "美丽湾工厂部", "phone": "13800138017"},
        {"name": "蒋义红", "position": "飞机盒主管", "group": "管理层", "dept": "美丽湾工厂部", "phone": "13800138018"},
        {"name": "沈齐豪", "position": "纸箱主管", "group": "管理层", "dept": "美丽湾工厂部", "phone": "13800138019"},
        {"name": "覃海霞", "position": "综合主管", "group": "管理层", "dept": "美丽湾工厂部", "phone": "13800138020"},
        # ===== 美丽湾工厂部-手啤机组 =====
        {"name": "李方国", "position": "手啤机-啤工", "group": "手啤机组", "dept": "美丽湾工厂部", "phone": "13800138021"},
        {"name": "李周海", "position": "手啤机-啤工", "group": "手啤机组", "dept": "美丽湾工厂部", "phone": "13800138022"},
        {"name": "唐美章", "position": "手啤机-啤工", "group": "手啤机组", "dept": "美丽湾工厂部", "phone": "13800138023"},
        {"name": "蒋保平", "position": "手啤机-啤工", "group": "手啤机组", "dept": "美丽湾工厂部", "phone": "13800138024"},
        {"name": "陈章远", "position": "手啤机-啤工", "group": "手啤机组", "dept": "美丽湾工厂部", "phone": "13800138025"},
        {"name": "黄振辉", "position": "手啤机-啤工", "group": "手啤机组", "dept": "美丽湾工厂部", "phone": "13800138026"},
        {"name": "汪成桃", "position": "手啤机-啤工", "group": "手啤机组", "dept": "美丽湾工厂部", "phone": "13800138027"},
        # ===== 美丽湾工厂部-啤机分组 =====
        {"name": "易新明", "position": "啤机分纸", "group": "啤机分组", "dept": "美丽湾工厂部", "phone": "13800138028"},
        {"name": "雷善炎", "position": "啤机分纸", "group": "啤机分组", "dept": "美丽湾工厂部", "phone": "13800138029"},
        {"name": "陈海斌", "position": "啤机分纸", "group": "啤机分组", "dept": "美丽湾工厂部", "phone": "13800138030"},
        {"name": "陈奕升", "position": "啤机分纸", "group": "啤机分组", "dept": "美丽湾工厂部", "phone": "13800138031"},
        {"name": "江旭松", "position": "啤机分纸", "group": "啤机分组", "dept": "美丽湾工厂部", "phone": "13800138032"},
        # ===== 美丽湾工厂部-刀模组 =====
        {"name": "廖金玲", "position": "刀模-找刀模", "group": "刀模组", "dept": "美丽湾工厂部", "phone": "13800138033"},
        {"name": "陈勇", "position": "刀模-组刀模", "group": "刀模组", "dept": "美丽湾工厂部", "phone": "13800138034"},
        {"name": "张吉杰", "position": "刀模-拆刀模", "group": "刀模组", "dept": "美丽湾工厂部", "phone": "13800138035"},
        {"name": "唐孝定", "position": "放刀模", "group": "刀模组", "dept": "美丽湾工厂部", "phone": "13800138036"},
        # ===== 美丽湾工厂部-机械手组 =====
        {"name": "黄恒", "position": "机械手啤工", "group": "机械手组", "dept": "美丽湾工厂部", "phone": "13800138037"},
        {"name": "李荣晖", "position": "机械手啤工", "group": "机械手组", "dept": "美丽湾工厂部", "phone": "13800138038"},
        # ===== 美丽湾工厂部-平压平组 =====
        {"name": "蒋森响", "position": "平压平啤工", "group": "平压平组", "dept": "美丽湾工厂部", "phone": "13800138039"},
        {"name": "周业福", "position": "平压平啤工", "group": "平压平组", "dept": "美丽湾工厂部", "phone": "13800138040"},
        # ===== 美丽湾工厂部-车间打包组 =====
        {"name": "陈桂英", "position": "车间打包", "group": "车间打包组", "dept": "美丽湾工厂部", "phone": "13800138041"},
        {"name": "毛良芬", "position": "车间打包", "group": "车间打包组", "dept": "美丽湾工厂部", "phone": "13800138042"},
        {"name": "陈辉文", "position": "车间打包", "group": "车间打包组", "dept": "美丽湾工厂部", "phone": "13800138043"},
        {"name": "文小梅", "position": "车间打包", "group": "车间打包组", "dept": "美丽湾工厂部", "phone": "13800138044"},
        {"name": "帅行朝", "position": "车间打包", "group": "车间打包组", "dept": "美丽湾工厂部", "phone": "13800138045"},
        {"name": "黄张华", "position": "车间打包", "group": "车间打包组", "dept": "美丽湾工厂部", "phone": "13800138046"},
        # ===== 美丽湾工厂部-仓库组 =====
        {"name": "宋小国", "position": "仓库-找货", "group": "仓库组", "dept": "美丽湾工厂部", "phone": "13800138047"},
        {"name": "唐忠群", "position": "仓库-找货", "group": "仓库组", "dept": "美丽湾工厂部", "phone": "13800138048"},
        {"name": "蒋仁叶", "position": "仓库-打包", "group": "仓库组", "dept": "美丽湾工厂部", "phone": "13800138049"},
        {"name": "罗照权", "position": "仓库-打包", "group": "仓库组", "dept": "美丽湾工厂部", "phone": "13800138050"},
        {"name": "黄爱小", "position": "仓库-放货", "group": "仓库组", "dept": "美丽湾工厂部", "phone": "13800138051"},
        {"name": "龙雪兰", "position": "仓库-打样兼配货", "group": "仓库组", "dept": "美丽湾工厂部", "phone": "13800138052"},
        # ===== 美丽湾工厂部-印刷组 =====
        {"name": "李双", "position": "印刷", "group": "印刷组", "dept": "美丽湾工厂部", "phone": "13800138053"},
        # ===== 美丽湾工厂部-扣底盒 =====
        {"name": "蒋军林", "position": "扣底盒", "group": "扣底盒组", "dept": "美丽湾工厂部", "phone": "13800138054"},
        {"name": "宁哈姝", "position": "扣底盒", "group": "扣底盒组", "dept": "美丽湾工厂部", "phone": "13800138055"},
        {"name": "黄华", "position": "扣底盒-打包", "group": "扣底盒组", "dept": "美丽湾工厂部", "phone": "13800138056"},
        # ===== 美丽湾工厂部-纸箱部(分纸) =====
        {"name": "陈伟", "position": "纸箱-分纸", "group": "纸箱分纸组", "dept": "美丽湾工厂部", "phone": "13800138057"},
        {"name": "陈陶", "position": "纸箱-分纸", "group": "纸箱分纸组", "dept": "美丽湾工厂部", "phone": "13800138058"},
        {"name": "周石国", "position": "纸箱-分纸", "group": "纸箱分纸组", "dept": "美丽湾工厂部", "phone": "13800138059"},
        # ===== 美丽湾工厂部-纸箱部(开槽) =====
        {"name": "杨家忠", "position": "纸箱-开槽", "group": "纸箱开槽组", "dept": "美丽湾工厂部", "phone": "13800138060"},
        {"name": "沈奇严", "position": "纸箱-开槽", "group": "纸箱开槽组", "dept": "美丽湾工厂部", "phone": "13800138061"},
        {"name": "姚建桥", "position": "纸箱-开槽", "group": "纸箱开槽组", "dept": "美丽湾工厂部", "phone": "13800138062"},
        # ===== 美丽湾工厂部-纸箱部(粘胶) =====
        {"name": "戴西华", "position": "纸箱-粘胶", "group": "纸箱粘胶组", "dept": "美丽湾工厂部", "phone": "13800138063"},
        {"name": "魏小王", "position": "纸箱-粘胶", "group": "纸箱粘胶组", "dept": "美丽湾工厂部", "phone": "13800138064"},
        {"name": "黄芳", "position": "纸箱-粘胶", "group": "纸箱粘胶组", "dept": "美丽湾工厂部", "phone": "13800138065"},
        {"name": "于天发", "position": "纸箱-粘胶/打角", "group": "纸箱粘胶组", "dept": "美丽湾工厂部", "phone": "13800138066"},
    ]
    statuses = _employee_today_status.get(today, {})

    lines = []
    lines.append('\ufeff' + '姓名,职务,厂区,手机号,今日状态')
    for emp in _employees_master_list:
        s = statuses.get(emp['name'], '出勤')
        lines.append(f"{emp['name']},{emp['position']},{emp['dept']},{emp['phone']},{s}")

    return Response(
        '\n'.join(lines),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=考勤报表_{today}.csv'}
    )


# ==================== 导出日报表CSV ====================
@app.route('/api/report/export')
def export_report():
    date = request.args.get('date', datetime.date.today().strftime('%Y-%m-%d'))
    # 模拟数据
    summary = {
        "total_orders": 45,
        "completed_orders": 14,
        "output_qty": 12500,
        "defect_rate": "1.2%",
    }
    production_lines = [
        {"line": "飞机盒线-自动平压平", "output": 5800, "status": "正常"},
        {"line": "飞机盒线-机械手", "output": 3200, "status": "正常"},
        {"line": "飞机盒线-手啤", "output": 1500, "status": "正常"},
        {"line": "纸箱线", "output": 2000, "status": "正常"},
    ]
    done_orders = [
        {"id": "JST-20260425-005", "product": "飞机盒20*15*10（现货）", "qty": 800, "last_step": "打包发货", "done_time": "16:00"},
        {"id": "JST-20260425-003", "product": "飞机盒25*15*10", "qty": 300, "last_step": "打包发货", "done_time": "15:30"},
        {"id": "JST-20260426-001", "product": "飞机盒30*20*15", "qty": 200, "last_step": "清废", "done_time": "14:20"},
    ]

    lines = []
    lines.append('\ufeff日报表 - ' + date)
    lines.append('')
    lines.append('指标,数值')
    lines.append(f'总单数,{summary["total_orders"]}')
    lines.append(f'完成数,{summary["completed_orders"]}')
    lines.append(f'总产出,{summary["output_qty"]}')
    lines.append(f'不良率,{summary["defect_rate"]}')
    lines.append('')
    lines.append('生产线,产出数,状态')
    for l in production_lines:
        lines.append(f'{l["line"]},{l["output"]},{l["status"]}')
    lines.append('')
    lines.append('内部单号,产品,数量,完成工序,完成时间')
    for o in done_orders:
        lines.append(f'{o["id"]},{o["product"]},{o["qty"]},{o["last_step"]},{o["done_time"]}')

    return Response(
        '\n'.join(lines),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=日报表_{date}.csv'}
    )


# ==================== 权限管理API ====================

# 功能列表（保持不变）
PERM_FEATURES = ["首页","订单生产进度","扫码报工","日报表","数据看板","刀模","库存","原材料","快麦ERP","员工","权限管理","报价","实时订单"]
_PERM_LEGACY_KEY = "聚水潭"
_PERM_CURRENT_KEY = "快麦ERP"


def _migrate_perm_dict(perms):
    if not isinstance(perms, dict):
        return perms
    if _PERM_LEGACY_KEY in perms and _PERM_CURRENT_KEY not in perms:
        perms[_PERM_CURRENT_KEY] = perms.pop(_PERM_LEGACY_KEY)
    elif _PERM_LEGACY_KEY in perms:
        perms.pop(_PERM_LEGACY_KEY, None)
    return perms

def _sync_all_employees_perms():
    """
    核心：确保_permission_data['permissions'] 包含所有员工且每个功能字段齐全。
    同步规则：
    - 超级管理员: 所有功能 true
    - 已有记录: 保留已有值，补全缺失字段为 false
    - 新员工(无记录): 所有功能 false
    每次保存和API返回前都调用，永不遗漏任何人。
    """
    base = _permission_data.setdefault("permissions", {})
    for emp in _employees_master_list:
        name = emp["name"]
        if name == "戴雅利":
            # 超级管理员全开
            if name not in base:
                base[name] = {}
            for f in PERM_FEATURES:
                base[name][f] = True
        elif name not in base:
            # 新员工默认全false
            base[name] = {}
            for f in PERM_FEATURES:
                base[name][f] = False
        else:
            _migrate_perm_dict(base[name])
            # 已有员工：补全缺失字段
            for f in PERM_FEATURES:
                if f not in base[name]:
                    base[name][f] = False
    # 清理已删除员工的残留权限
    valid_names = {e["name"] for e in _employees_master_list}
    for name in list(base.keys()):
        if name not in valid_names:
            del base[name]
    _permission_data["permissions"] = base

# 初始化时执行一次
_sync_all_employees_perms()

_permission_data_init = {
    "processes": ["客服接单", "黄厂打印", "审单分单", "算料", "分纸", "啤机(自动平压平)", "啤机(机械手)", "手啤", "印刷", "开槽/打角", "清废", "打包发货"],
    "positions": ["超级管理员", "主管", "客服", "员工", "财务", "业务员"],
    "employees": [
        {"name": "戴雅利", "position": "超级管理员"},
        {"name": "邓涛", "position": "主管"},
        {"name": "黄兴", "position": "主管"},
        {"name": "覃海霞", "position": "主管"},
        {"name": "蒋义红", "position": "主管"},
        {"name": "沈齐豪", "position": "主管"},
        {"name": "苏世婷", "position": "客服"},
        {"name": "廖思美", "position": "客服"},
        {"name": "张慧平", "position": "客服"},
        {"name": "陈贝贝", "position": "客服"},
        {"name": "罗怡", "position": "客服"},
        {"name": "周井梅", "position": "客服"},
        {"name": "戴志美", "position": "客服"},
        {"name": "石梅清", "position": "客服"},
        {"name": "张文杰", "position": "客服"},
        {"name": "何水单", "position": "业务员"},
        {"name": "李四军", "position": "员工"},
        {"name": "陈贤聪", "position": "业务员"},
        {"name": "姚斌", "position": "员工"},
        {"name": "隆浪", "position": "财务"},
    ],
    "permissions": {}
}
# 确保默认结构与现有数据合并
for key, default_val in _permission_data_init.items():
    if key not in _permission_data:
        _permission_data[key] = default_val
# 再次同步权限
_sync_all_employees_perms()

@app.route('/api/permissions/data')
def get_permissions_data():
    # 每次返回都同步一次，保证永远不遗漏
    _sync_all_employees_perms()
    return jsonify(_permission_data)

@app.route('/api/permissions/save', methods=['POST'])
def save_permissions_data():
    global _permission_data
    data = request.get_json()
    if data:
        # 更新结构数据
        if "processes" in data:
            _permission_data["processes"] = data["processes"]
        if "positions" in data:
            _permission_data["positions"] = data["positions"]
        # 合并权限：用新数据覆盖旧数据
        new_perms = data.get("permissions", {})
        if new_perms:
            old_perms = _permission_data.setdefault("permissions", {})
            for name, feats in new_perms.items():
                if name not in old_perms:
                    old_perms[name] = {}
                old_perms[name].update(feats)
        # 更新员工启用/禁用状态
        new_enabled = data.get("employee_enabled")
        if new_enabled is not None:
            _permission_data["employee_enabled"] = new_enabled
        # 同步全员工，保证每个人每个字段都不缺
        _sync_all_employees_perms()
        persist()
    return jsonify({"success": True, "message": "权限配置已保存"})

@app.route('/api/processes')
def get_processes():
    return jsonify({"processes": _permission_data.get("processes", [])})

@app.route('/api/process_tree')
def get_process_tree():
    """返回树形工序结构"""
    return jsonify({"tree": _permission_data.get("processes", [])})


@app.route('/api/my_permissions')
def get_my_permissions():
    """返回当前登录用户的完整权限映射"""
    if 'username' not in session:
        return jsonify({"error": "未登录"}), 401
    user = USERS.get(session['username'])
    if not user:
        return jsonify({"error": "用户不存在"}), 401
    name = user['employee_name']
    _sync_all_employees_perms()
    all_perms = _permission_data.get("permissions", {})
    # 系统账号（admin）直接全权限
    if user.get("is_system"):
        my_perm = {f: True for f in PERM_FEATURES}
    else:
        my_perm = all_perms.get(name, {})
    return jsonify({
        "success": True,
        "my_permissions": my_perm,
        "all_permissions": all_perms,
        "all_employees": _employees_master_list
    })


@app.route('/api/processes/save', methods=['POST'])
def save_processes():
    global _permission_data
    data = request.get_json()
    if data and 'processes' in data:
        _permission_data['processes'] = data['processes']
    return jsonify({"success": True, "message": "流程已保存"})

# ==================== 扫码报工-可选操作人（按角色过滤） ====================
@app.route('/api/scan_workers')
def scan_workers():
    """根据当前用户角色返回可选择的操作人列表"""
    if 'username' not in session:
        return jsonify({"error": "未登录", "code": 401}), 401
    user = USERS.get(session['username'])
    if not user:
        return jsonify({"error": "用户不存在", "code": 401}), 401
    
    role = user['role']
    current_name = user['employee_name']
    all_emps = _employees_master_list
    
    if role == '超级管理员':
        # 返回所有美丽湾工厂部员工（车间扫码报工用）
        workers = [e for e in all_emps if e['dept'] == '美丽湾工厂部']
    elif role == '管理':
        # 管理只能选美丽湾工厂部的
        workers = [e for e in all_emps if e['dept'] == '美丽湾工厂部']
    elif role == '客服':
        # 客服只能选洋坑塘运营部的（扫码报工用，可能不需要，但留着）
        workers = [e for e in all_emps if e['dept'] == '洋坑塘运营部']
    elif role == '员工':
        # 员工只能选自己
        workers = [e for e in all_emps if e['name'] == current_name]
    else:
        workers = []
    
    return jsonify({"workers": workers})

# ==================== 报价系统 ====================
QUOTE_DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'quote_data.json')

def load_quote_data():
    try:
        with open(QUOTE_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None

def save_quote_data(qd):
    try:
        with open(QUOTE_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(qd, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

def ceil_to_half(val):
    """向上取整到0.5：23.32→23.5, 23.62→24"""
    import math
    return math.ceil(val * 2) / 2

def ceil_to_spec(val, spec_list, multiply_limit=3):
    """纸箱度数取整：如果val不在spec_list中，尝试×2/×3取奇数再除"""
    import math
    
    # 先检查val本身是否在规格表中或大于等于最小规格
    min_spec = min(spec_list)
    if val >= min_spec:
        for s in spec_list:
            if val <= s:
                return s
        # 超过最大规格，取最大
        return max(spec_list)
    
    # val小于最小规格，尝试×multiply
    for mult in range(2, multiply_limit + 1):
        multiplied = val * mult
        # 取大于multiplied的奇数（纸箱度数都是奇数）
        ceil_odd = math.ceil(multiplied)
        if ceil_odd % 2 == 0:
            ceil_odd += 1
        # 检查这个奇数是否能在spec_list中找到
        if ceil_odd >= min_spec:
            for s in spec_list:
                if ceil_odd <= s:
                    return s / mult
            return max(spec_list) / mult
    
    # 保底
    return min_spec / multiply_limit

def calc_airbox(length, width, height, qty, material_key, quote_data, is_buckle=False):
    """标准飞机盒/带扣飞机盒报价"""
    import math
    
    # 纸长/纸度公式
    if is_buckle:
        paper_l_cm = 3 * height + 2 * width + 3
    else:
        paper_l_cm = 3 * height + 2 * width
    
    paper_w_cm = length + 4 * height + 4
    
    # 取整到0.5
    paper_l_inch = ceil_to_half(paper_l_cm / 2.54)
    paper_w_inch = ceil_to_half(paper_w_cm / 2.54)
    
    # 获取材料单价
    mat_config = quote_data.get("materials", {}).get("airbox", {}).get("materials", {})
    mat_info = mat_config.get(material_key, {})
    unit_price = mat_info.get("price", 1.35)
    mat_name = mat_info.get("name", material_key)
    
    # 材料成本 = 纸长×纸度×单价/1000
    material_cost_per_unit = paper_l_inch * paper_w_inch * unit_price / 1000
    
    # 零售价 = 材料成本 × 2
    retail_mult = quote_data.get("profit", {}).get("retail_multiplier", 2.0)
    sell_price_per_unit = material_cost_per_unit * retail_mult
    
    # 批量建议
    suggestions = quote_data.get("profit", {}).get("suggestions", {}).get("airbox", [])
    suggested_rate = None
    for s in sorted(suggestions, key=lambda x: -x["qty"]):
        if qty >= s["qty"]:
            suggested_rate = s["multiplier"]
            break

    # ====== 重量计算 ======
    # 展开面积(平方英寸) = 纸长×纸度
    # 转平方米: 1平方英寸 = 0.00064516 平方米
    gram_weight = mat_info.get("gram_weight", 450)  # 克/平方米
    area_m2 = paper_l_inch * paper_w_inch * 0.00064516
    weight_per_unit_g = area_m2 * gram_weight
    weight_per_unit_kg = weight_per_unit_g / 1000

    # ====== 快递费（首重+续重） ======
    freight_config = quote_data.get("freight", {})
    total_weight_kg = weight_per_unit_kg * qty

    def calc_freight(total_kg, cfg):
        first = cfg.get("first_kg", 10)
        renew = cfg.get("renew_per_kg", 0.9)
        if total_kg <= 1:
            return round(first, 2)
        else:
            extra = total_kg - 1
            return round(first + extra * renew, 2)

    freight_total_gd = calc_freight(total_weight_kg, freight_config.get("guangdong", {}))
    freight_total_jzh = calc_freight(total_weight_kg, freight_config.get("jiangzhehu", {}))
    freight_total_other = calc_freight(total_weight_kg, freight_config.get("other", {}))

    freight_per_unit_gd = round(freight_total_gd / qty, 4)
    freight_per_unit_jzh = round(freight_total_jzh / qty, 4)
    freight_per_unit_other = round(freight_total_other / qty, 4)

    return {
        "product": "带扣飞机盒" if is_buckle else "标准飞机盒",
        "material_key": material_key,
        "material_name": mat_name,
        "unit_price": unit_price,
        "gram_weight": gram_weight,
        "paper_l_cm": round(paper_l_cm, 1),
        "paper_w_cm": round(paper_w_cm, 1),
        "paper_l_inch": round(paper_l_inch, 2),
        "paper_w_inch": round(paper_w_inch, 2),
        "material_cost_per_unit": round(material_cost_per_unit, 4),
        "retail_multiplier": retail_mult,
        "sell_price_per_unit": round(sell_price_per_unit, 4),
        "total_cost": round(material_cost_per_unit * qty, 2),
        "total_price": round(sell_price_per_unit * qty, 2),
        "qty": qty,
        "suggested_multiplier": suggested_rate,
        "suggested_price": round(material_cost_per_unit * suggested_rate, 4) if suggested_rate else None,
        "weight_per_unit_g": round(weight_per_unit_g, 2),
        "weight_per_unit_kg": round(weight_per_unit_kg, 4),
        "weight_total_kg": round(total_weight_kg, 2),
        "freight_per_unit_gd": freight_per_unit_gd,
        "freight_per_unit_jzh": freight_per_unit_jzh,
        "freight_per_unit_other": freight_per_unit_other,
        "freight_total_gd": freight_total_gd,
        "freight_total_jzh": freight_total_jzh,
        "freight_total_other": freight_total_other
    }

def calc_koudi(length, width, height, qty, material_key, quote_data):
    """扣底盒报价"""
    import math
    
    # 纸长 = (长×2 + 宽×2 + 3) / 2.54
    paper_l_cm = length * 2 + width * 2 + 3
    # 纸度 = (宽 + 高 + 1/2宽 + 3 + 2) / 2.54
    paper_w_cm = width + height + width / 2 + 3 + 2
    
    paper_l_inch = ceil_to_half(paper_l_cm / 2.54)
    paper_w_inch = ceil_to_half(paper_w_cm / 2.54)
    
    # 获取材料单价（扣底盒体系）
    mat_config = quote_data.get("materials", {}).get("koudi", {}).get("materials", {})
    mat_info = mat_config.get(material_key, {})
    unit_price = mat_info.get("price", 1.40)
    mat_name = mat_info.get("name", material_key)
    
    material_cost_per_unit = paper_l_inch * paper_w_inch * unit_price / 1000
    retail_mult = quote_data.get("profit", {}).get("retail_multiplier", 2.0)
    sell_price_per_unit = material_cost_per_unit * retail_mult

    # ====== 重量计算 ======
    gram_weight = mat_info.get("gram_weight", 450)
    area_m2 = paper_l_inch * paper_w_inch * 0.00064516
    weight_per_unit_g = area_m2 * gram_weight
    weight_per_unit_kg = weight_per_unit_g / 1000

    # ====== 快递费（首重+续重） ======
    freight_config = quote_data.get("freight", {})
    total_weight_kg = weight_per_unit_kg * qty

    def calc_freight(total_kg, cfg):
        first = cfg.get("first_kg", 10)
        renew = cfg.get("renew_per_kg", 0.9)
        if total_kg <= 1:
            return round(first, 2)
        else:
            extra = total_kg - 1
            return round(first + extra * renew, 2)

    freight_total_gd = calc_freight(total_weight_kg, freight_config.get("guangdong", {}))
    freight_total_jzh = calc_freight(total_weight_kg, freight_config.get("jiangzhehu", {}))
    freight_total_other = calc_freight(total_weight_kg, freight_config.get("other", {}))

    freight_per_unit_gd = round(freight_total_gd / qty, 4)
    freight_per_unit_jzh = round(freight_total_jzh / qty, 4)
    freight_per_unit_other = round(freight_total_other / qty, 4)

    return {
        "product": "扣底盒",
        "material_key": material_key,
        "material_name": mat_name,
        "unit_price": unit_price,
        "gram_weight": gram_weight,
        "paper_l_cm": round(paper_l_cm, 1),
        "paper_w_cm": round(paper_w_cm, 1),
        "paper_l_inch": round(paper_l_inch, 2),
        "paper_w_inch": round(paper_w_inch, 2),
        "material_cost_per_unit": round(material_cost_per_unit, 4),
        "retail_multiplier": retail_mult,
        "sell_price_per_unit": round(sell_price_per_unit, 4),
        "total_cost": round(material_cost_per_unit * qty, 2),
        "total_price": round(sell_price_per_unit * qty, 2),
        "qty": qty,
        "suggested_multiplier": None,
        "suggested_price": None,
        "weight_per_unit_g": round(weight_per_unit_g, 2),
        "weight_per_unit_kg": round(weight_per_unit_kg, 4),
        "weight_total_kg": round(total_weight_kg, 2),
        "freight_per_unit_gd": freight_per_unit_gd,
        "freight_per_unit_jzh": freight_per_unit_jzh,
        "freight_per_unit_other": freight_per_unit_other,
        "freight_total_gd": freight_total_gd,
        "freight_total_jzh": freight_total_jzh,
        "freight_total_other": freight_total_other
    }

def calc_shuangcha(length, width, height, qty, material_key, quote_data):
    """双插盒报价"""
    import math
    
    # 纸长 = (长×2 + 宽×2 + 3) / 2.54
    paper_l_cm = length * 2 + width * 2 + 3
    # 纸度 = (宽×2 + 6 + 高) / 2.54
    paper_w_cm = width * 2 + 6 + height
    
    paper_l_inch = ceil_to_half(paper_l_cm / 2.54)
    paper_w_inch = ceil_to_half(paper_w_cm / 2.54)
    
    # 获取材料单价（扣底盒体系，跟扣底盒用同一套）
    mat_config = quote_data.get("materials", {}).get("koudi", {}).get("materials", {})
    mat_info = mat_config.get(material_key, {})
    unit_price = mat_info.get("price", 1.40)
    mat_name = mat_info.get("name", material_key)
    
    material_cost_per_unit = paper_l_inch * paper_w_inch * unit_price / 1000
    retail_mult = quote_data.get("profit", {}).get("retail_multiplier", 2.0)
    sell_price_per_unit = material_cost_per_unit * retail_mult

    # ====== 重量计算 ======
    gram_weight = mat_info.get("gram_weight", 450)
    area_m2 = paper_l_inch * paper_w_inch * 0.00064516
    weight_per_unit_g = area_m2 * gram_weight
    weight_per_unit_kg = weight_per_unit_g / 1000

    # ====== 快递费（首重+续重） ======
    freight_config = quote_data.get("freight", {})
    total_weight_kg = weight_per_unit_kg * qty

    def calc_freight(total_kg, cfg):
        first = cfg.get("first_kg", 10)
        renew = cfg.get("renew_per_kg", 0.9)
        if total_kg <= 1:
            return round(first, 2)
        else:
            extra = total_kg - 1
            return round(first + extra * renew, 2)

    freight_total_gd = calc_freight(total_weight_kg, freight_config.get("guangdong", {}))
    freight_total_jzh = calc_freight(total_weight_kg, freight_config.get("jiangzhehu", {}))
    freight_total_other = calc_freight(total_weight_kg, freight_config.get("other", {}))

    freight_per_unit_gd = round(freight_total_gd / qty, 4)
    freight_per_unit_jzh = round(freight_total_jzh / qty, 4)
    freight_per_unit_other = round(freight_total_other / qty, 4)

    return {
        "product": "双插盒",
        "material_key": material_key,
        "material_name": mat_name,
        "unit_price": unit_price,
        "gram_weight": gram_weight,
        "paper_l_cm": round(paper_l_cm, 1),
        "paper_w_cm": round(paper_w_cm, 1),
        "paper_l_inch": round(paper_l_inch, 2),
        "paper_w_inch": round(paper_w_inch, 2),
        "material_cost_per_unit": round(material_cost_per_unit, 4),
        "retail_multiplier": retail_mult,
        "sell_price_per_unit": round(sell_price_per_unit, 4),
        "total_cost": round(material_cost_per_unit * qty, 2),
        "total_price": round(sell_price_per_unit * qty, 2),
        "qty": qty,
        "suggested_multiplier": None,
        "suggested_price": None,
        "weight_per_unit_g": round(weight_per_unit_g, 2),
        "weight_per_unit_kg": round(weight_per_unit_kg, 4),
        "weight_total_kg": round(total_weight_kg, 2),
        "freight_per_unit_gd": freight_per_unit_gd,
        "freight_per_unit_jzh": freight_per_unit_jzh,
        "freight_per_unit_other": freight_per_unit_other,
        "freight_total_gd": freight_total_gd,
        "freight_total_jzh": freight_total_jzh,
        "freight_total_other": freight_total_other
    }

def calc_carton(length, width, height, qty, material_key, quote_data):
    """纸箱报价"""
    import math
    
    specs = quote_data.get("cardboard_specs", {})
    paper_lengths = specs.get("danbu_paper_lengths", [29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90])
    paper_widths = specs.get("danbu_paper_widths", [29,31,33,35,37,39,41,43,45,47,49])
    max_danbu_cm = specs.get("max_danbu_length_cm", 230)
    
    # 判断单卜还是双卜
    danbu_paper_l_cm = (length + width) * 2 + 3.5
    is_double = danbu_paper_l_cm > max_danbu_cm
    
    if is_double:
        # 双卜
        paper_l_cm = ((length + width) + 3.5) * 2
    else:
        # 单卜
        paper_l_cm = danbu_paper_l_cm
    
    paper_w_cm = width + height + 0.6
    
    # 纸长取整到度数表
    paper_l_raw = paper_l_cm / 2.54
    paper_l_inch = ceil_to_spec(paper_l_raw, paper_lengths)
    
    # 纸度取整到度数表
    paper_w_raw = paper_w_cm / 2.54
    paper_w_inch = ceil_to_spec(paper_w_raw, paper_widths)
    
    # 获取材料单价（纸箱体系）
    mat_config = quote_data.get("materials", {}).get("carton", {}).get("materials", {})
    mat_info = mat_config.get(material_key, {})
    unit_price = mat_info.get("price", 1.30)
    mat_name = mat_info.get("name", material_key)
    
    material_cost_per_unit = paper_l_inch * paper_w_inch * unit_price / 1000
    retail_mult = quote_data.get("profit", {}).get("retail_multiplier", 2.0)
    sell_price_per_unit = material_cost_per_unit * retail_mult

    # ====== 重量计算 ======
    gram_weight = mat_info.get("gram_weight", 380)
    area_m2 = paper_l_inch * paper_w_inch * 0.00064516
    weight_per_unit_g = area_m2 * gram_weight
    weight_per_unit_kg = weight_per_unit_g / 1000

    # ====== 快递费（首重+续重） ======
    freight_config = quote_data.get("freight", {})
    total_weight_kg = weight_per_unit_kg * qty

    def calc_freight(total_kg, cfg):
        first = cfg.get("first_kg", 10)
        renew = cfg.get("renew_per_kg", 0.9)
        if total_kg <= 1:
            return round(first, 2)
        else:
            extra = total_kg - 1
            return round(first + extra * renew, 2)

    freight_total_gd = calc_freight(total_weight_kg, freight_config.get("guangdong", {}))
    freight_total_jzh = calc_freight(total_weight_kg, freight_config.get("jiangzhehu", {}))
    freight_total_other = calc_freight(total_weight_kg, freight_config.get("other", {}))

    freight_per_unit_gd = round(freight_total_gd / qty, 4)
    freight_per_unit_jzh = round(freight_total_jzh / qty, 4)
    freight_per_unit_other = round(freight_total_other / qty, 4)

    return {
        "product": "双卜纸箱" if is_double else "单卜纸箱",
        "material_key": material_key,
        "material_name": mat_name,
        "unit_price": unit_price,
        "gram_weight": gram_weight,
        "paper_l_cm": round(paper_l_cm, 1),
        "paper_w_cm": round(paper_w_cm, 1),
        "paper_l_inch": round(paper_l_inch, 2),
        "paper_w_inch": round(paper_w_inch, 2),
        "material_cost_per_unit": round(material_cost_per_unit, 4),
        "retail_multiplier": retail_mult,
        "sell_price_per_unit": round(sell_price_per_unit, 4),
        "total_cost": round(material_cost_per_unit * qty, 2),
        "total_price": round(sell_price_per_unit * qty, 2),
        "qty": qty,
        "is_double_buckle": is_double,
        "suggested_multiplier": None,
        "suggested_price": None,
        "weight_per_unit_g": round(weight_per_unit_g, 2),
        "weight_per_unit_kg": round(weight_per_unit_kg, 4),
        "weight_total_kg": round(total_weight_kg, 2),
        "freight_per_unit_gd": freight_per_unit_gd,
        "freight_per_unit_jzh": freight_per_unit_jzh,
        "freight_per_unit_other": freight_per_unit_other,
        "freight_total_gd": freight_total_gd,
        "freight_total_jzh": freight_total_jzh,
        "freight_total_other": freight_total_other
    }

@app.route('/api/quote_data')
def get_quote_data():
    """返回报价基础数据（保持JSON key顺序）"""
    try:
        with open(QUOTE_DATA_FILE, 'r', encoding='utf-8') as f:
            raw = f.read()
        return '{"success":true,"data":' + raw + '}', 200, {'Content-Type': 'application/json'}
    except:
        return jsonify({"success": False, "error": "报价数据未加载"})

@app.route('/api/quote/save_config', methods=['POST'])
def save_quote_config():
    """保存报价配置（仅权限管理角色可操作）"""
    try:
        # 检查权限
        if 'username' not in session:
            return jsonify({"success": False, "error": "未登录"})
        user = USERS.get(session['username'])
        if not user:
            return jsonify({"success": False, "error": "用户不存在"})
        name = user['employee_name']
        _sync_all_employees_perms()
        my_perm = _permission_data.get("permissions", {}).get(name, {})
        if not my_perm.get('权限管理', False):
            return jsonify({"success": False, "error": "无权限修改报价配置"})
        
        new_data = request.get_json()
        if not new_data:
            return jsonify({"success": False, "error": "数据为空"})
        
        if save_quote_data(new_data):
            return jsonify({"success": True, "message": "报价配置已保存"})
        else:
            return jsonify({"success": False, "error": "保存失败"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/quote/calculate', methods=['POST'])
def calculate_quote():
    """计算报价"""
    try:
        data = request.get_json()
        ptype = data.get('type', 'zhengsquare')  # zhengsquare, juxing, daikou, koudi, shuangcha, qita
        length = float(data.get('length', 0))
        width = float(data.get('width', 0))
        height = float(data.get('height', 0))
        qty = int(data.get('qty', 1000))
        material = data.get('material', 'd6d')
        discount = float(data.get('discount', 100)) / 100.0  # 折扣百分比转小数

        if length <= 0 or width <= 0 or height <= 0:
            return jsonify({"error": "请输入正确的尺寸", "success": False})
        
        import math

        qd = load_quote_data()
        if not qd:
            return jsonify({"error": "报价数据未加载", "success": False})

        # 兼容 zhengsquare-outer / zhengsquare-inner
        # 内径转外径：长+1.5cm，宽+0.5cm，高+0.5cm
        if ptype == 'zhengsquare-inner':
            length = length + 1.5
            width = width + 0.5
            height = height + 0.5
        
        base_type = ptype.replace('-outer', '').replace('-inner', '')
        if base_type == 'zhengsquare':
            detail = calc_airbox(length, width, height, qty, material, qd, is_buckle=False)
            # 标注外径/内径
            if ptype == 'zhengsquare-inner':
                detail['dimension_label'] = '内径转外径'
            else:
                detail['dimension_label'] = '外径'
        elif base_type == 'juxing':
            detail = calc_airbox(length, width, height, qty, material, qd, is_buckle=False)
        elif ptype == 'daikou':
            detail = calc_airbox(length, width, height, qty, material, qd, is_buckle=True)
        elif ptype == 'koudi':
            detail = calc_koudi(length, width, height, qty, material, qd)
        elif ptype == 'shuangcha':
            detail = calc_shuangcha(length, width, height, qty, material, qd)
        elif ptype == 'qita':
            detail = calc_carton(length, width, height, qty, material, qd)
        elif ptype == 'pe':
            # 珍珠棉报价 - 输入单位毫米
            length_m = length / 1000  # 毫米转米
            width_m = width / 1000    # 毫米转米
            
            # 厚度向上取整到0.5mm的倍数（0.5阶梯）
            # 0~0.5→0.5, 0.6~1.0→1.0, 1.1~1.5→1.5, 1.6~2.0→2.0
            height_raw = height  # 保留原始值用于显示
            height = math.ceil(height / 0.5) * 0.5
            if height == 0:
                height = 0.5  # 最小0.5
            
            pe_price = qd.get("materials", {}).get("pe", {}).get("price", 0.3)
            material_cost_per_unit = length_m * width_m * height * pe_price
            
            # 客户类型
            customer_type = data.get('customer_type', 'guangdong_wholesale')
            customer_types = qd.get("materials", {}).get("pe", {}).get("customer_types", {})
            ct_info = customer_types.get(customer_type, {})
            multiplier = ct_info.get("multiplier", 2.0)
            ct_name = ct_info.get("name", customer_type)
            
            sell_price_per_unit = material_cost_per_unit * multiplier
            retail_mult = qd.get("profit", {}).get("retail_multiplier", 2.0)
            
            # 总货款判断
            total_price = sell_price_per_unit * qty
            total_price_discounted = total_price * discount
            price_too_low = total_price_discounted < 100  # 总货款低于100元
            unit_price_too_low = sell_price_per_unit < 0.3  # 单价低于0.3元
            
            # 重量预估（泡比5000）和快递费
            height_cm = height / 10  # 毫米转厘米
            length_cm = length / 10  # 毫米转厘米
            width_cm = width / 10    # 毫米转厘米
            weight_per_unit_kg = height_cm * length_cm * width_cm / 5000
            
            # 快递费（首重+续重）
            freight_config = qd.get("materials", {}).get("pe", {}).get("freight", {})
            
            def calc_freight(total_kg, cfg):
                first = cfg.get("first_kg", 10)
                renew = cfg.get("renew_per_kg", 0.9)
                if total_kg <= 1:
                    return round(first, 2)
                else:
                    extra = total_kg - 1
                    return round(first + extra * renew, 2)
            
            freight_per_unit_gd = round(calc_freight(weight_per_unit_kg, freight_config.get("guangdong", {})), 4)
            freight_per_unit_jzh = round(calc_freight(weight_per_unit_kg, freight_config.get("jiangzhehu", {})), 4)
            freight_per_unit_other = round(calc_freight(weight_per_unit_kg, freight_config.get("other", {})), 4)
            
            total_weight_kg = weight_per_unit_kg * qty
            freight_total_gd = calc_freight(total_weight_kg, freight_config.get("guangdong", {}))
            freight_total_jzh = calc_freight(total_weight_kg, freight_config.get("jiangzhehu", {}))
            freight_total_other = calc_freight(total_weight_kg, freight_config.get("other", {}))
            
            detail = {
                "product": "珍珠棉片材",
                "material_name": "珍珠棉",
                "unit_price": pe_price,
                "length_m": round(length_m, 4),
                "width_m": round(width_m, 4),
                "thickness_mm": height,
                "thickness_input_mm": height_raw,
                "customer_type": ct_name,
                "multiplier": multiplier,
                "material_cost_per_unit": round(material_cost_per_unit, 4),
                "retail_multiplier": retail_mult,
                "sell_price_per_unit": round(sell_price_per_unit, 4),
                "total_cost": round(material_cost_per_unit * qty, 2),
                "total_price": round(total_price, 2),
                "total_price_discounted": round(total_price_discounted, 2),
                "sell_price_per_unit_discounted": round(sell_price_per_unit * discount, 4),
                "qty": qty,
                "weight_per_unit_kg": round(weight_per_unit_kg, 4),
                "weight_total_kg": round(total_weight_kg, 2),
                "freight_per_unit_gd": freight_per_unit_gd,
                "freight_per_unit_jzh": freight_per_unit_jzh,
                "freight_per_unit_other": freight_per_unit_other,
                "freight_total_gd": freight_total_gd,
                "freight_total_jzh": freight_total_jzh,
                "freight_total_other": freight_total_other,
                "discount": round(discount * 100, 1),
                "suggested_multiplier": None,
                "suggested_price": None,
                "pe_warning_price_too_low": price_too_low,
                "pe_warning_unit_price_too_low": unit_price_too_low
            }
        else:
            return jsonify({"error": "未知的产品类型", "success": False})

        # 应用折扣
        detail["discount"] = round(discount * 100, 1)
        detail["sell_price_per_unit_discounted"] = round(detail["sell_price_per_unit"] * discount, 4)
        detail["total_price_discounted"] = round(detail["total_price"] * discount, 2)

        return jsonify({"success": True, "detail": detail})

    except Exception as e:
        return jsonify({"error": str(e), "success": False})

# ==================== 固定刀模库 API ====================
DIEMOLD_FILE = os.path.join(os.path.dirname(__file__), 'dimoldb.json')

def load_dimoldb():
    """加载刀模库数据"""
    if not os.path.exists(DIEMOLD_FILE):
        return []
    try:
        with open(DIEMOLD_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_dimoldb(data):
    """保存刀模库数据"""
    with open(DIEMOLD_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _has_dimoldb_edit_perm():
    """检查是否有刀模库编辑权限"""
    if 'username' not in session:
        return False
    user = USERS.get(session['username'])
    if not user:
        return False
    if user['role'] in ('超级管理员', '管理'):
        return True
    # 检查功能权限
    _sync_all_employees_perms()
    name = user['employee_name']
    my_perm = _permission_data.get("permissions", {}).get(name, {})
    if my_perm.get('刀模管理', False):
        return True
    return False


def _dimoldb_infer_inner_outer(dm):
    """内外径：优先 dim_type；为空时用 name 中 (内)/内径/(外)/外径 及 remark 中的 内/外 字推断。返回 inner|outer|''。"""
    dt = (dm.get('dim_type') or '').strip()
    if dt == 'inner':
        return 'inner'
    if dt == 'outer':
        return 'outer'
    name = dm.get('name') or ''
    rk = dm.get('remark') or ''
    if '(内)' in name or '内径' in name or '内' in rk:
        return 'inner'
    if '(外)' in name or '外径' in name or '外' in rk:
        return 'outer'
    return ''


@app.route('/api/dimoldb', methods=['GET'])
def get_dimoldb():
    """获取刀模列表（支持分页）"""
    data = load_dimoldb()
    # 支持筛选
    ptype = request.args.get('type', '')
    search = request.args.get('search', '').strip()
    dim_type = request.args.get('dim_type', '').strip()
    if ptype:
        # 兼容 zhengsquare-outer / zhengsquare-inner（dim_type 为空时 name/remark 推断，与客服端一致）
        if ptype == 'zhengsquare-outer':
            data = [d for d in data if d.get('product_type') == 'zhengsquare' and _dimoldb_infer_inner_outer(d) == 'outer']
        elif ptype == 'zhengsquare-inner':
            data = [d for d in data if d.get('product_type') == 'zhengsquare' and _dimoldb_infer_inner_outer(d) == 'inner']
        else:
            data = [d for d in data if d.get('product_type') == ptype]
    if dim_type and not ptype.startswith('zhengsquare-'):
        data = [d for d in data if _dimoldb_infer_inner_outer(d) == dim_type]
    if search:
        # 刀模搜索统一用正则提取数字，兼容所有分隔符（x/*/×/空格...）
        nums = re.findall(r'\d+\.?\d*', search.replace(' ', '*'))
        nums = [n for n in nums if n.strip()]
        if len(nums) >= 3:
            try:
                sl = float(nums[0].strip())
                sw = float(nums[1].strip())
                sh = float(nums[2].strip())
                data = [d for d in data if 
                    d.get('length') is not None and abs(d['length'] - sl) < 0.1 and
                    d.get('width') is not None and abs(d['width'] - sw) < 0.1 and
                    d.get('height') is not None and abs(d['height'] - sh) < 0.1]
            except:
                pass
        else:
            data = [d for d in data if search in d.get('name', '') or f"{d.get('length',0)}x{d.get('width',0)}x{d.get('height',0)}" in search or f"{d.get('length',0)}×{d.get('width',0)}×{d.get('height',0)}" in search]
    # 分页
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 50))
    except ValueError:
        page, page_size = 1, 50
    if page < 1: page = 1
    if page_size < 1: page_size = 50
    if page_size > 200: page_size = 200
    total = len(data)
    total_pages = max(1, (total + page_size - 1) // page_size)
    start = (page - 1) * page_size
    end = start + page_size
    page_data = data[start:end] if start < total else []
    # 给每条刀模补充真实库存数（从inventory.json统计）
    inv_all = load_inventory()
    inv_items = inv_all.get('finished', inv_all if isinstance(inv_all, list) else [])
    def calc_stock(dm):
        """根据刀模的尺寸+dim_type统计库存总量"""
        dm_l = dm.get('length')
        dm_w = dm.get('width')
        dm_h = dm.get('height')
        dm_dt = (dm.get('dim_type') or '').strip()
        # 刀模 dim_type 为空：name / remark 推断内外径（与客服端一致）
        if not dm_dt:
            dm_dt = _dimoldb_infer_inner_outer(dm)
        dm_type = dm.get('product_type', '')
        # 刀模类型→库存类型映射：库存只有 changfang 和 zhengsquare
        _type_map = {
            'zhengsquare': 'zhengsquare',
            'juxing': 'changfang',
            'daikou': 'changfang',
            'koudi': 'changfang',
            'shuangcha': 'changfang',
            'qita': 'changfang',
        }
        inv_type_map = _type_map.get(dm_type, dm_type)
        total = 0
        for iv in inv_items:
            iv_l = iv.get('length')
            iv_w = iv.get('width')
            iv_h = iv.get('height')
            if not (iv_l and iv_w and iv_h and dm_l and dm_w and dm_h):
                continue
            if abs(float(iv_l) - float(dm_l)) >= 0.1: continue
            if abs(float(iv_w) - float(dm_w)) >= 0.1: continue
            if abs(float(iv_h) - float(dm_h)) >= 0.1: continue
            # 匹配dim_type（内外径要分开）
            iv_dt = iv.get('dim_type', '')
            if dm_dt and iv_dt and dm_dt != iv_dt:
                continue
            # 匹配product_type：刀模类型→库存类型映射
            iv_type = iv.get('product_type', '')
            if iv_type and iv_type != inv_type_map:
                continue
            total += int(iv.get('qty') or iv.get('stock') or 0)
        return total
    for d in page_data:
        d['stock'] = calc_stock(d)
    return jsonify({
        "success": True,
        "data": page_data,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "can_edit": _has_dimoldb_edit_perm()
    })

@app.route('/api/dimoldb/single', methods=['GET'])
def get_dimoldb_single():
    """根据ID获取单个刀模"""
    dm_id = request.args.get('id', '').strip()
    if not dm_id:
        return jsonify({"success": False, "error": "缺少id参数"})
    data = load_dimoldb()
    for d in data:
        if d.get('id') == dm_id:
            return jsonify({"success": True, "data": d})
    return jsonify({"success": False, "error": "未找到"})

@app.route('/api/dimoldb', methods=['POST'])
def add_dimoldb():
    """新增刀模"""
    if not _has_dimoldb_edit_perm():
        return jsonify({"success": False, "error": "无权限"})
    try:
        item = request.get_json()
        required = ['product_type', 'name', 'length', 'width', 'height']
        for k in required:
            if k not in item:
                return jsonify({"success": False, "error": f"缺少字段: {k}"})
        data = load_dimoldb()
        item['id'] = f"dm_{int(time.time())}_{len(data)}"
        item['created_at'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        data.append(item)
        save_dimoldb(data)
        return jsonify({"success": True, "message": "刀模已添加"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/dimoldb/<dm_id>', methods=['PUT'])
def update_dimoldb(dm_id):
    """修改刀模"""
    if not _has_dimoldb_edit_perm():
        return jsonify({"success": False, "error": "无权限"})
    try:
        item = request.get_json()
        data = load_dimoldb()
        for d in data:
            if d.get('id') == dm_id:
                d.update(item)
                d['id'] = dm_id
                save_dimoldb(data)
                return jsonify({"success": True, "message": "刀模已更新"})
        return jsonify({"success": False, "error": "未找到该刀模"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/dimoldb/<dm_id>', methods=['DELETE'])
def delete_dimoldb(dm_id):
    """删除刀模"""
    if not _has_dimoldb_edit_perm():
        return jsonify({"success": False, "error": "无权限"})
    data = load_dimoldb()
    new_data = [d for d in data if d.get('id') != dm_id]
    if len(new_data) == len(data):
        return jsonify({"success": False, "error": "未找到该刀模"})
    save_dimoldb(new_data)
    return jsonify({"success": True, "message": "刀模已删除"})

@app.route('/api/dimoldb/export', methods=['GET'])
def export_dimoldb():
    """导出所有刀模为Excel"""
    try:
        import openpyxl
        from openpyxl.styles import Font, Alignment, Border, Side
        db = load_dimoldb()
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = '刀模库'
        headers = ['序号', '产品类型', '名称', '编码', '备注', '长(cm)', '宽(cm)', '高(cm)', '创建时间']
        thin = Border(
            left=Side(style='thin'), right=Side(style='thin'),
            top=Side(style='thin'), bottom=Side(style='thin'))
        header_font = Font(bold=True, size=11)
        for ci, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=ci, value=h)
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center')
            cell.border = thin
        for ri, item in enumerate(db, 2):
            vals = [
                ri - 1,
                item.get('product_type', ''),
                item.get('name', ''),
                item.get('code', '') or '',
                item.get('remark', '') or '',
                item.get('length', ''),
                item.get('width', ''),
                item.get('height', ''),
                item.get('created_at', '')
            ]
            for ci, v in enumerate(vals, 1):
                cell = ws.cell(row=ri, column=ci, value=v)
                cell.border = thin
        ws.column_dimensions['A'].width = 6
        ws.column_dimensions['B'].width = 16
        ws.column_dimensions['C'].width = 30
        ws.column_dimensions['D'].width = 14
        ws.column_dimensions['E'].width = 20
        ws.column_dimensions['F'].width = 10
        ws.column_dimensions['G'].width = 10
        ws.column_dimensions['H'].width = 10
        ws.column_dimensions['I'].width = 18
        import tempfile
        tmp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        wb.save(tmp.name)
        tmp.close()
        import flask
        resp = flask.send_file(tmp.name, as_attachment=True, download_name=f'刀模库_{datetime.date.today().isoformat()}.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        return resp
    except Exception as e:
        import traceback
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500

@app.route('/api/dimoldb/import', methods=['POST'])
def import_dimoldb():
    """上传Excel导入刀模"""
    if not _has_dimoldb_edit_perm():
        return jsonify({"success": False, "error": "无权限"})
    try:
        import openpyxl
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "请上传Excel文件"})
        f = request.files['file']
        if f.filename == '':
            return jsonify({"success": False, "error": "未选择文件"})
        import tempfile
        tmp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        f.save(tmp.name)
        tmp.close()
        wb = openpyxl.load_workbook(tmp.name, data_only=True)
        ws = wb.active
        # 探测表头
        header_row = None
        for r_idx, row in enumerate(ws.iter_rows(min_row=1, max_row=5, values_only=True), 1):
            vals = [str(v or '').strip() for v in row]
            if '名称' in vals or '刀模名称' in vals or 'name' in vals:
                header_row = r_idx
                break
        if header_row is None:
            return jsonify({"success": False, "error": "未找到表头行（需包含'名称'列）"})
        headers = [str(v or '').strip() for v in next(ws.iter_rows(min_row=header_row, max_row=header_row, values_only=True))]
        col_map = {}
        for i, h in enumerate(headers):
            if '名称' in h or h == 'name':
                col_map['name'] = i
            elif '类型' in h or '产品' in h or 'product' in h.lower():
                col_map['product_type'] = i
            elif '编码' in h or 'code' in h.lower():
                col_map['code'] = i
            elif '备注' in h or 'remark' in h.lower():
                col_map['remark'] = i
            elif '长' in h or 'length' in h.lower():
                col_map['length'] = i
            elif '宽' in h or 'width' in h.lower():
                col_map['width'] = i
            elif '高' in h or 'height' in h.lower():
                col_map['height'] = i
        if 'name' not in col_map:
            return jsonify({"success": False, "error": f"未找到'名称'列，表头: {headers}"})
        db = load_dimoldb()
        added = 0
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        for row in ws.iter_rows(min_row=header_row + 1, values_only=True):
            name = str(row[col_map['name']]).strip() if col_map['name'] < len(row) and row[col_map['name']] else ''
            if not name or name.startswith('=') or name == 'None':
                continue
            item = {
                'id': f'dm_{int(time.time())}_{added}_{len(db)}',
                'name': name,
                'product_type': str(row[col_map['product_type']]).strip() if col_map.get('product_type') is not None and col_map['product_type'] < len(row) and row[col_map['product_type']] else 'zhengsquare',
                'code': str(row[col_map['code']]).strip() if col_map.get('code') is not None and col_map['code'] < len(row) and row[col_map['code']] else '',
                'remark': str(row[col_map['remark']]).strip() if col_map.get('remark') is not None and col_map['remark'] < len(row) and row[col_map['remark']] else '',
                'length': float(row[col_map['length']]) if col_map.get('length') is not None and col_map['length'] < len(row) and row[col_map['length']] is not None else 0,
                'width': float(row[col_map['width']]) if col_map.get('width') is not None and col_map['width'] < len(row) and row[col_map['width']] is not None else 0,
                'height': float(row[col_map['height']]) if col_map.get('height') is not None and col_map['height'] < len(row) and row[col_map['height']] is not None else 0,
                'created_at': now
            }
            try:
                item['length'] = float(item['length'])
            except: item['length'] = 0
            try:
                item['width'] = float(item['width'])
            except: item['width'] = 0
            try:
                item['height'] = float(item['height'])
            except: item['height'] = 0
            db.append(item)
            added += 1
        save_dimoldb(db)
        import os
        try: os.unlink(tmp.name)
        except: pass
        return jsonify({"success": True, "message": f"导入完成，新增 {added} 条刀模记录", "added": added})
    except Exception as e:
        import traceback
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()})

# -------------------- 库存导出 --------------------
@app.route('/api/inventory/export', methods=['GET'])
def export_inventory():
    """导出库存为Excel"""
    try:
        import openpyxl
        from openpyxl.styles import Font, Alignment, Border, Side
        tab = request.args.get('tab', 'finished')
        data = load_inventory()
        items = data.get(tab, [])
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = '库存'
        headers = ['序号', '名称', '产品类型', '内/外径', '材质', '库存', '长(cm)', '宽(cm)', '高(cm)', '货位', '备注', '更新时间']
        thin = Border(
            left=Side(style='thin'), right=Side(style='thin'),
            top=Side(style='thin'), bottom=Side(style='thin'))
        header_font = Font(bold=True, size=11)
        for ci, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=ci, value=h)
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center')
            cell.border = thin
        for ri, item in enumerate(items, 2):
            dim_label = {'inner': '内径', 'outer': '外径'}.get(item.get('dim_type', ''), '')
            vals = [
                ri - 1,
                item.get('name', ''),
                item.get('product_type', ''),
                dim_label,
                item.get('material', ''),
                int(item.get('stock', item.get('qty', 0))),
                item.get('length', ''),
                item.get('width', ''),
                item.get('height', ''),
                item.get('location', '') or '',
                item.get('remark', '') or '',
                item.get('updated_at', item.get('created_at', ''))
            ]
            for ci, v in enumerate(vals, 1):
                cell = ws.cell(row=ri, column=ci, value=v)
                cell.border = thin
        for col_letter, width in zip('ABCDEFGHIJKL', [6, 30, 12, 10, 12, 8, 10, 10, 10, 12, 20, 18]):
            ws.column_dimensions[col_letter].width = width
        import tempfile
        tmp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        wb.save(tmp.name)
        tmp.close()
        tab_label = {'finished': '成品', 'returned': '退货'}.get(tab, tab)
        import flask
        resp = flask.send_file(tmp.name, as_attachment=True, download_name=f'{tab_label}库存_{datetime.date.today().isoformat()}.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        return resp
    except Exception as e:
        import traceback
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500

@app.route('/api/dimoldb/search', methods=['POST'])
def search_dimoldb():
    """查询某尺寸是否有固定刀模（供报价系统调用）"""
    try:
        data = request.get_json()
        ptype = data.get('type', '')
        length = data.get('length')
        width = data.get('width')
        height = data.get('height')
        dim_type = data.get('dim_type', '')
        db = load_dimoldb()
        matches = db
        if ptype:
            # 兼容 zhengsquare-outer / zhengsquare-inner
            actual_type = ptype.replace('-outer', '').replace('-inner', '')
            matches = [d for d in matches if d.get('product_type') == actual_type]
            # 如果ptype带内外径但dim_type没传，自动设置
            if 'outer' in ptype and not data.get('dim_type'):
                dim_type = 'outer'
            elif 'inner' in ptype and not data.get('dim_type'):
                dim_type = 'inner'
        if length is not None:
            lv = float(length)
            matches = [d for d in matches if abs(float(d.get('length', 0)) - lv) < 0.1]
        if width is not None:
            wv = float(width)
            matches = [d for d in matches if abs(float(d.get('width', 0)) - wv) < 0.1]
        if height is not None:
            hv = float(height)
            matches = [d for d in matches if abs(float(d.get('height', 0)) - hv) < 0.1]
        # 内外径过滤：dim_type 为空时用 name/remark 推断（与客服端 search_dimoldb 一致）
        ptype_for_dim = data.get('type', '')
        if dim_type and ptype_for_dim == 'zhengsquare':
            if dim_type == 'inner':
                matches = [d for d in matches if _dimoldb_infer_inner_outer(d) == 'inner']
            elif dim_type == 'outer':
                matches = [d for d in matches if _dimoldb_infer_inner_outer(d) == 'outer']
        elif dim_type and ptype_for_dim not in ('zhengsquare', '', None):
            has_inner_outer = any(_dimoldb_infer_inner_outer(d) for d in matches)
            if has_inner_outer and dim_type:
                if dim_type == 'inner':
                    matches = [d for d in matches if _dimoldb_infer_inner_outer(d) == 'inner']
                elif dim_type == 'outer':
                    matches = [d for d in matches if _dimoldb_infer_inner_outer(d) == 'outer']
        return jsonify({"success": True, "matches": matches})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# ==================== 库存 API ====================
INVENTORY_FILE = os.path.join(os.path.dirname(__file__), 'inventory.json')

def load_inventory():
    if not os.path.exists(INVENTORY_FILE):
        return {"finished": [], "raw": [], "returned": []}
    try:
        with open(INVENTORY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):
            return {"finished": data, "raw": [], "returned": []}
        return data
    except:
        return {"finished": [], "raw": [], "returned": []}

def save_inventory(data):
    # 如果是最顶层列表格式，保持原样
    if isinstance(data, dict):
        # 检查文件原始格式：如果原来存的是列表，提取finished
        if os.path.exists(INVENTORY_FILE):
            try:
                orig = json.load(open(INVENTORY_FILE, 'r', encoding='utf-8'))
                if isinstance(orig, list):
                    data = data.get('finished', data.get('raw', []))
            except:
                pass
    with open(INVENTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _has_inv_edit_perm():
    """库存修改权限：超级管理员/管理/有'库存'权限"""
    if 'username' not in session:
        return False
    user = USERS.get(session['username'])
    if not user:
        return False
    if user['role'] in ('超级管理员', '管理'):
        return True
    _sync_all_employees_perms()
    name = user['employee_name']
    my_perm = _permission_data.get("permissions", {}).get(name, {})
    if my_perm.get('库存', False):
        return True
    return False

@app.route('/api/inventory', methods=['GET'])
def get_inventory():
    """获取库存列表（支持分页，同刀模库）"""
    tab = request.args.get('tab', 'finished')
    data = load_inventory()
    items = data.get(tab, [])
    
    # 材质映射函数：库存中的材质名 → 显示名
    def map_material(m):
        mapping = {
            '国产纸': '特硬D6D',
            '双白': '白色W7W',
            '台湾纸': '台湾纸',
            '黑色': '黑色',
            '红色': '红色',
            '差材料': '差材料'
        }
        return mapping.get(m.strip(), m.strip()) if m else ''
    
    # 给所有item做材质映射
    for item in items:
        if item.get('material'):
            item['material'] = map_material(item['material'])
        # name 中也替换材质名
        n = item.get('name', '')
        for old, new in [('国产纸','特硬D6D'), ('双白','白色W7W')]:
            if old in n:
                item['name'] = n.replace(old, new)
                n = item['name']
    
    ptype = request.args.get('type', '')
    search = request.args.get('search', '').strip()
    length = request.args.get('length', '').strip()
    width = request.args.get('width', '').strip()
    height = request.args.get('height', '').strip()
    if ptype == 'zhengsquare-outer':
        items = [d for d in items if d.get('product_type') == 'zhengsquare' and d.get('dim_type') == 'outer']
    elif ptype == 'zhengsquare-inner':
        items = [d for d in items if d.get('product_type') == 'zhengsquare' and d.get('dim_type') == 'inner']
    elif ptype:
        # 库存只有 changfang 和 zhengsquare，刀模type需要映射
        _type_to_inv = {'juxing':'changfang', 'daikou':'changfang', 'koudi':'changfang', 'shuangcha':'changfang', 'qita':'changfang', 'changfang':'changfang', 'zhengsquare':'zhengsquare'}
        inv_type = _type_to_inv.get(ptype, ptype)
        items = [d for d in items if d.get('product_type') == inv_type]
    if search:
        # 【通用提取】提取输入中的前三个数字，不管分隔符是什么
        # 支持: 10x10x2, 10*10*2, 10×10×2, 10 10 2, 10,10,2, 10-10-2, 10.10.2 等全部格式
        nums = re.findall(r'\d+\.?\d*', search.replace(' ', '*'))
        nums = [n for n in nums if n.strip()]
        if len(nums) >= 3:
            try:
                sl = float(nums[0].strip())
                sw = float(nums[1].strip())
                sh = float(nums[2].strip())
                items = [d for d in items if 
                    d.get('length') is not None and abs(d['length'] - sl) < 0.1 and
                    d.get('width') is not None and abs(d['width'] - sw) < 0.1 and
                    d.get('height') is not None and abs(d['height'] - sh) < 0.1]
            except:
                pass
        elif search.replace('.','').replace('-','').isdigit() or search.strip().replace('.','').replace('-','').replace(',','').replace('|','').lstrip('-').isdigit():
            # 纯数字搜索
            sv = float(search.strip().lstrip('-').replace(',','.'))
            items = [d for d in items if 
                (d.get('length') is not None and abs(d['length'] - sv) < 0.1) or
                (d.get('width') is not None and abs(d['width'] - sv) < 0.1) or
                (d.get('height') is not None and abs(d['height'] - sv) < 0.1)]
        else:
            search_field = request.args.get('search_field', 'all')
            if search_field == 'name':
                items = [d for d in items if search in d.get('name', '')]
            elif search_field == 'material':
                items = [d for d in items if search in d.get('material', '')]
            else:
                # 通用搜索
                items = [d for d in items if 
                    search in d.get('name', '') or
                    search in d.get('material', '')]
    if length:
        lv = float(length)
        items = [d for d in items if d.get('length') is not None and abs(float(d['length']) - lv) < 0.1]
    if width:
        wv = float(width)
        items = [d for d in items if d.get('width') is not None and abs(float(d['width']) - wv) < 0.1]
    if height:
        hv = float(height)
        items = [d for d in items if d.get('height') is not None and abs(float(d['height']) - hv) < 0.1]
    # 按尺寸从小到大排序
    def sort_key(item):
        try:
            dims = item.get('name', '').replace('×','*').replace('x','*').replace('X','*').split('*')
            l, w, h = float(dims[0]), float(dims[1]), float(dims[2])
            return (l, w, h)
        except:
            return (9999, 9999, 9999)
    items.sort(key=sort_key)
    # 分页
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 50))
    except ValueError:
        page, page_size = 1, 50
    if page < 1: page = 1
    if page_size < 1: page_size = 50
    if page_size > 200: page_size = 200
    total = len(items)
    total_pages = max(1, (total + page_size - 1) // page_size)
    start = (page - 1) * page_size
    end = start + page_size
    page_data = items[start:end] if start < total else []
    # 兼容前端stock字段 + 在name中标明内外径 + 反缓存
    for item in page_data:
        if 'stock' not in item and 'qty' in item:
            item['stock'] = item['qty']
        if item.get('dim_type') == 'inner' and not item['name'].startswith('内径'):
            item['name'] = '内径' + item['name']
        elif item.get('dim_type') == 'outer' and not item['name'].startswith('外径') and not item['name'].startswith('内'):
            item['name'] = '外径' + item['name']
        # 匹配对应刀模（按尺寸+内外径）
        dm_info = []
        try:
            db = load_dimoldb()
            l, w, h = item.get('length'), item.get('width'), item.get('height')
            itype = item.get('product_type')
            idim = item.get('dim_type', '')
            if l and w and h and itype:
                candidates = [d for d in db if d.get('product_type') == itype
                    and abs(float(d.get('length', 0)) - float(l)) < 0.1
                    and abs(float(d.get('width', 0)) - float(w)) < 0.1
                    and abs(float(d.get('height', 0)) - float(h)) < 0.1]
                # 内外径过滤（基于刀模 name 与 remark，与客服端一致）
                if idim == 'outer':
                    candidates = [d for d in candidates if '(外)' in d.get('name', '') or ('外' in (d.get('remark') or ''))]
                elif idim == 'inner':
                    candidates = [d for d in candidates if '(内)' in d.get('name', '') or ('内' in (d.get('remark') or ''))]
                if not idim:
                    iname = item.get('name', '')
                    if iname.startswith('内径'):
                        candidates = [d for d in candidates if '(内)' in d.get('name', '') or ('内' in (d.get('remark') or ''))]
                    else:
                        candidates = [d for d in candidates if '(外)' in d.get('name', '') or ('外' in (d.get('remark') or ''))]
                for dm in candidates:
                    dm_info.append({
                        'id': dm.get('id', ''),
                        'name': dm.get('name', ''),
                        'code': dm.get('code', '') or '',
                        'remark': dm.get('remark', '') or ''
                    })
        except: pass
        item['dimoldb_info'] = dm_info
    resp = jsonify({
        "success": True,
        "data": page_data,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "can_edit": _has_inv_edit_perm()
    })
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    return resp

@app.route('/api/inventory', methods=['POST'])
def add_inventory():
    if not _has_inv_edit_perm():
        return jsonify({"success": False, "error": "无权限"})
    try:
        item = request.get_json()
        tab = item.get('tab', 'finished')
        if 'name' not in item:
            return jsonify({"success": False, "error": "缺少名称"})
        data = load_inventory()
        item['id'] = f"inv_{int(time.time())}_{len(data.get(tab, []))}"
        item['created_at'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        item['updated_at'] = item['created_at']
        if tab not in data:
            data[tab] = []
        data[tab].append(item)
        save_inventory(data)
        return jsonify({"success": True, "message": "已添加"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/inventory/<item_id>', methods=['PUT'])
def update_inventory(item_id):
    if not _has_inv_edit_perm():
        return jsonify({"success": False, "error": "无权限"})
    try:
        item = request.get_json()
        data = load_inventory()
        for tab in ('finished', 'raw'):
            for d in data.get(tab, []):
                if d.get('id') == item_id:
                    d.update(item)
                    d['id'] = item_id
                    d['updated_at'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
                    save_inventory(data)
                    return jsonify({"success": True, "message": "已更新"})
        return jsonify({"success": False, "error": "未找到"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/inventory/<item_id>', methods=['DELETE'])
def delete_inventory(item_id):
    if not _has_inv_edit_perm():
        return jsonify({"success": False, "error": "无权限"})
    data = load_inventory()
    for tab in ('finished', 'raw'):
        before = len(data.get(tab, []))
        data[tab] = [d for d in data.get(tab, []) if d.get('id') != item_id]
        if len(data[tab]) < before:
            save_inventory(data)
            return jsonify({"success": True, "message": "已删除"})
    return jsonify({"success": False, "error": "未找到"})

@app.route('/api/inventory/stock', methods=['POST'])
def stock_operation():
    """入库/出库操作（带log记录）"""
    if not _has_inv_edit_perm():
        return jsonify({"success": False, "error": "无权限"})
    try:
        body = request.get_json()
        item_id = body.get('id')
        op = body.get('op', 'in')
        qty = int(body.get('qty', 0))
        remark = body.get('remark', '').strip()
        if not item_id or qty <= 0:
            return jsonify({"success": False, "error": "参数错误"})
        # 获取操作人
        operator = ''
        if 'username' in session:
            operator = USERS.get(session['username'], {}).get('employee_name', session['username'])
        data = load_inventory()
        for tab in ('finished', 'raw'):
            for d in data.get(tab, []):
                if d.get('id') == item_id:
                    current = int(d.get('stock', 0))
                    if op == 'in':
                        d['stock'] = current + qty
                    else:
                        if current < qty:
                            return jsonify({"success": False, "error": f"库存不足！当前{current}，出库{qty}"})
                        d['stock'] = current - qty
                    d['updated_at'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
                    # 写log
                    if 'inout_log' not in d:
                        d['inout_log'] = []
                    op_label = '入库' if op == 'in' else '出库'
                    before_stock = current
                    after_stock = d['stock']
                    d['inout_log'].append({
                        "time": d['updated_at'],
                        "op": op,
                        "op_label": op_label,
                        "qty": qty,
                        "before": before_stock,
                        "after": after_stock,
                        "operator": operator,
                        "remark": remark
                    })
                    save_inventory(data)
                    return jsonify({
                        "success": True,
                        "message": f"{op_label}成功（{before_stock} → {after_stock}）",
                        "new_stock": d['stock']
                    })
        return jsonify({"success": False, "error": "未找到该商品"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/inventory/<item_id>/log', methods=['GET'])
def get_inventory_log(item_id):
    """获取某商品的出入库历史记录"""
    data = load_inventory()
    for tab in ('finished', 'raw'):
        for d in data.get(tab, []):
            if d.get('id') == item_id:
                log = d.get('inout_log', [])
                return jsonify({
                    "success": True,
                    "item_name": d.get('name', ''),
                    "current_stock": d.get('stock', 0),
                    "log": log
                })
    return jsonify({"success": False, "error": "未找到该商品"})

@app.route('/api/inventory/single', methods=['GET'])
def get_inventory_single():
    """根据ID获取单个库存商品"""
    item_id = request.args.get('id', '').strip()
    if not item_id:
        return jsonify({"success": False, "error": "缺少ID"})
    data = load_inventory()
    for tab in ('finished', 'raw'):
        for d in data.get(tab, []):
            if d.get('id') == item_id:
                return jsonify({"success": True, "data": d})
    return jsonify({"success": False, "error": "未找到该商品"})


@app.route('/api/inventory/import_excel', methods=['POST'])
def import_inventory_excel():
    """导入excel库存台账"""
    if not _has_inv_edit_perm():
        return jsonify({"success": False, "error": "无权限"})
    try:
        import openpyxl
        # 检查是否有上传文件
        if 'file' in request.files:
            f = request.files['file']
            if f.filename == '':
                return jsonify({"success": False, "error": "未选择文件"})
            import tempfile
            tmp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
            f.save(tmp.name)
            tmp.close()
            filepath = tmp.name
        else:
            # 兼容旧模式：从缓存目录查找
            data = request.get_json() or {}
            filepath = data.get('filepath', '')
            if not os.path.isabs(filepath):
                cache_dir = '/home/admin/.hermes/cache/documents/'
                if os.path.exists(cache_dir):
                    candidates = [f for f in os.listdir(cache_dir) if filepath in f and f.endswith('.xlsx')]
                    if candidates:
                        filepath = os.path.join(cache_dir, sorted(candidates, key=lambda f: os.path.getmtime(os.path.join(cache_dir, f)), reverse=True)[0])
            if not filepath or not os.path.exists(filepath):
                return jsonify({"success": False, "error": "未找到文件"})
        
        sheet_name = request.form.get('sheet_name', '') if 'file' in request.files else data.get('sheet', '')
        product_type = request.form.get('product_type', 'zhengsquare') if 'file' in request.files else data.get('product_type', 'zhengsquare')
        
        wb = openpyxl.load_workbook(filepath, data_only=True)
        # 找对应sheet
        if sheet_name:
            if sheet_name not in wb.sheetnames:
                return jsonify({"success": False, "error": f"未找到工作表: {sheet_name}，可用的: {wb.sheetnames}"})
            ws = wb[sheet_name]
        else:
            ws = wb.active
        
        inv_data = load_inventory()
        tab = 'finished'
        added = 0
        
        # 自动探测表头行（找包含"外尺寸"的行）
        header_row = None
        for r_idx, row in enumerate(ws.iter_rows(min_row=1, max_row=10, values_only=True), 1):
            vals = [str(v or '') for v in row[:8]]
            if '外尺寸' in vals or '外尺寸规格' in vals:
                header_row = r_idx
                break
        
        if header_row is None:
            return jsonify({"success": False, "error": "未找到表头行（需包含外尺寸）"})
        
        # 确定列索引
        header = [str(v or '') for v in next(ws.iter_rows(min_row=header_row, max_row=header_row, values_only=True))]
        col_map = {}
        for i, h in enumerate(header):
            h_clean = h.strip()
            if '外尺寸' in h_clean:
                col_map['spec'] = i
            elif '材质' in h_clean:
                col_map['material'] = i
            elif '货位' in h_clean or '货 位' in h_clean:
                col_map['location'] = i
            elif '上月' in h_clean or '上月库存' in h_clean:
                col_map['last_month'] = i
            elif '入库' in h_clean and '数量' in h_clean:
                col_map['in_qty'] = i
            elif '出库' in h_clean and '数量' in h_clean:
                col_map['out_qty'] = i
            elif '剩余' in h_clean or '库存' in h_clean:
                col_map['stock'] = i
            elif '序号' in h_clean:
                col_map['seq'] = i
        if 'spec' not in col_map:
            return jsonify({"success": False, "error": f"未找到'外尺寸'列，表头: {header}"})
        
        # 读取数据行：从header_row之后找到第一个有规格的行
        data_start = header_row + 1
        for r_idx in range(header_row + 1, min(header_row + 10, ws.max_row + 1)):
            row = list(ws.iter_rows(min_row=r_idx, max_row=r_idx, values_only=True))[0]
            if col_map['spec'] < len(row):
                spec_val = row[col_map['spec']]
                spec_str = str(spec_val).strip() if spec_val else ''
                if spec_val and spec_str and not spec_str.startswith('=') and not spec_str.startswith('#'):
                    try:
                        dims = spec_str.replace('×','*').replace('x','*').split('*')
                        if len(dims) >= 3:
                            data_start = r_idx
                            break
                    except:
                        pass
        
        for row in ws.iter_rows(min_row=data_start, values_only=True):
            spec = row[col_map['spec']] if col_map['spec'] < len(row) else None
            if not spec or not str(spec).strip():
                continue
            spec = str(spec).strip()
            # 跳过公式行（=ROW开头）
            if spec.startswith('=') or spec.startswith('#'):
                continue
            
            # 解析规格：如 "10.5×7.5×4.5" 或 "6×6×2"
            dims = spec.replace('×', '*').replace('x', '*').replace('X', '*').split('*')
            length = width = height = None
            try:
                if len(dims) >= 3:
                    length = float(dims[0].strip())
                    width = float(dims[1].strip())
                    height = float(dims[2].strip())
            except:
                pass
            
            # 材质（可能有多个材质行共享同一个规格）
            material = str(row[col_map['material']]).strip() if col_map.get('material') and col_map['material'] < len(row) and row[col_map['material']] else ''
            location = str(row[col_map['location']]).strip() if col_map.get('location') and col_map['location'] < len(row) and row[col_map['location']] else ''
            
            # 数值
            last_month = 0
            stock_qty = 0
            try:
                v = row[col_map['last_month']] if col_map.get('last_month') and col_map['last_month'] < len(row) else 0
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    last_month = int(v)
            except: pass
            try:
                v = row[col_map['stock']] if col_map.get('stock') and col_map['stock'] < len(row) else 0
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    stock_qty = int(v)
            except: pass
            
            # 构造商品名
            name_parts = [spec]
            if material and material not in ('None', ''):
                name_parts.append(material)
            name = ' '.join(name_parts)
            
            # 去重：同名+同产品类型 不重复导入
            exists = False
            for d in inv_data[tab]:
                if d.get('name') == name and d.get('product_type') == product_type:
                    exists = True
                    break
            
            if not exists:
                item_id = f"inv_{int(time.time())}_{added}_{len(inv_data[tab])}"
                item = {
                    'id': item_id,
                    'name': name,
                    'spec': spec,
                    'product_type': product_type,
                    'material': material,
                    'location': location,
                    'qty': stock_qty,
                    'last_month_qty': last_month,
                    'length': length,
                    'width': width,
                    'height': height,
                    'created_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
                    'updated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
                }
                inv_data[tab].append(item)
                added += 1
        
        save_inventory(inv_data)
        return jsonify({"success": True, "message": f"导入完成，新增 {added} 条记录", "added": added})
    except Exception as e:
        import traceback
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()})

# ==================== 权限列表 ====================
@app.route('/api/permissions')
def permissions():
    return jsonify({
        "roles": [
            {"name": "超级管理员", "desc": "所有权限", "count": 2},
            {"name": "主管", "desc": "生产管理、员工查看", "count": 5},
            {"name": "客服", "desc": "订单查看、生产进度", "count": 10},
            {"name": "员工", "desc": "扫码报工、查看任务", "count": 20},
        ]
    })


# ==================== 静态文件 ====================
@app.route('/login_simple')
def login_simple():
    return send_from_directory('.', 'simple_login.html')

# ==================== 原材料库存 API ====================
RAW_DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'raw_data.json')

def load_raw_data():
    if not os.path.exists(RAW_DATA_FILE):
        return []
    try:
        with open(RAW_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_raw_data(data):
    with open(RAW_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.route('/api/raw', methods=['GET'])
def get_raw():
    data = load_raw_data()
    search = request.args.get('search', '').strip()
    date = request.args.get('date', '').strip()
    name = request.args.get('name', '').strip()
    supplier = request.args.get('supplier', '').strip()
    paper_width = request.args.get('paper_width', '').strip()
    paper_length = request.args.get('paper_length', '').strip()
    if date:
        data = [d for d in data if date in d.get('date', '')]
    if name:
        data = [d for d in data if name.lower() in d.get('name', '').lower()]
    if supplier:
        data = [d for d in data if supplier.lower() in d.get('supplier', '').lower()]
    if paper_width:
        data = [d for d in data if str(d.get('paper_width', '')) == paper_width]
    if paper_length:
        data = [d for d in data if str(d.get('paper_length', '')) == paper_length]
    if search:
        data = [d for d in data if search.lower() in d.get('name', '').lower() or search.lower() in d.get('remark', '').lower()]
    data.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return jsonify({"success": True, "data": data})

@app.route('/api/raw', methods=['POST'])
def add_raw():
    body = request.get_json()
    if not body or not body.get('name', '').strip():
        return jsonify({"success": False, "error": "材料名称不能为空"})
    data = load_raw_data()
    new_id = str(int(time.time() * 1000)) + str(len(data))
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    entry = {
        "id": new_id,
        "date": body.get('date', '').strip(),
        "name": body['name'].strip(),
        "supplier": body.get('supplier', '').strip(),
        "paper_width": body.get('paper_width', ''),
        "paper_length": body.get('paper_length', ''),
        "qty": int(body.get('qty', 0)),
        "remark": body.get('remark', '').strip(),
        "created_at": now,
        "updated_at": now
    }
    data.append(entry)
    save_raw_data(data)
    return jsonify({"success": True, "data": entry, "message": "原材料保存成功"})

@app.route('/api/raw/<raw_id>', methods=['PUT'])
def update_raw(raw_id):
    body = request.get_json()
    data = load_raw_data()
    for item in data:
        if item['id'] == raw_id:
            if body.get('date', '').strip(): item['date'] = body['date'].strip()
            if body.get('name', '').strip(): item['name'] = body['name'].strip()
            if 'supplier' in body: item['supplier'] = body['supplier'].strip()
            if 'paper_width' in body: item['paper_width'] = str(body['paper_width'])
            if 'paper_length' in body: item['paper_length'] = str(body['paper_length'])
            if 'qty' in body: item['qty'] = int(body['qty'])
            if 'remark' in body: item['remark'] = body['remark'].strip()
            item['updated_at'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
            save_raw_data(data)
            return jsonify({"success": True, "data": item, "message": "更新成功"})
    return jsonify({"success": False, "error": "未找到该材料"})

@app.route('/api/raw/stock', methods=['POST'])
def raw_stock():
    body = request.get_json()
    rid = body.get('id', '')
    op = body.get('op', 'in')
    qty = int(body.get('qty', 0))
    if qty <= 0:
        return jsonify({"success": False, "error": "数量必须大于0"})
    data = load_raw_data()
    for item in data:
        if item['id'] == rid:
            if op == 'in':
                item['qty'] = (item.get('qty', 0) or 0) + qty
            else:
                item['qty'] = max(0, (item.get('qty', 0) or 0) - qty)
            item['updated_at'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
            save_raw_data(data)
            return jsonify({"success": True, "data": item, "message": f"{'入库' if op=='in' else '出库'}成功"})
    return jsonify({"success": False, "error": "未找到该材料"})

# ==================== 静态文件 ====================
@app.route('/')
def index():
    resp = make_response(send_from_directory('.', 'index.html'))
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('.', path)



from io import BytesIO
import qrcode
import barcode
from barcode.writer import ImageWriter
import base64

# ===== 二维码 & 条码生成 =====
@app.route('/api/barcode/<order_id>')
def generate_barcode(order_id):
    """生成订单条码（Code128，base64图片）"""
    try:
        code = barcode.get('code128', order_id, writer=ImageWriter())
        buf = BytesIO()
        code.write(buf)
        b64 = base64.b64encode(buf.getvalue()).decode()
        return jsonify({'success': True, 'barcode_base64': b64})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/qrcode/<order_id>')
def generate_qrcode(order_id):
    """生成订单二维码（base64图片）"""
    # 二维码内容：扫码后打开报工页面
    qr_data = f"{request.host_url}scan?order={order_id}"
    img = qrcode.make(qr_data, box_size=8)
    buf = BytesIO()
    img.save(buf, format='PNG')
    b64 = base64.b64encode(buf.getvalue()).decode()
    return jsonify({'success': True, 'qr_base64': b64, 'url': qr_data})

# ===== 扫码报工手机专用页 =====
@app.route('/scan')
def scan_page():
    """手机扫码后打开的报工页面"""
    order_id = request.args.get('order', '')
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no">
<title>三羊包装 - 扫码报工</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system,sans-serif; background:#f5f6fa; min-height:100vh; display:flex; flex-direction:column; align-items:center; padding:20px; }}
.card {{ background:#fff; border-radius:16px; padding:24px; width:100%; max-width:420px; box-shadow:0 2px 12px rgba(0,0,0,0.08); text-align:center; }}
.order-id {{ font-size:24px; font-weight:800; color:#1a1a2e; margin:12px 0; word-break:break-all; }}
.step-btn {{ display:block; width:100%; padding:14px; margin:8px 0; border:none; border-radius:10px; font-size:15px; font-weight:600; cursor:pointer; transition:all 0.2s; }}
.step-btn:active {{ transform:scale(0.97); }}
.btn-primary {{ background:#1677ff; color:#fff; }}
.btn-success {{ background:#52c41a; color:#fff; }}
.btn-gray {{ background:#f0f0f0; color:#666; }}
.info {{ font-size:13px; color:#999; margin:8px 0; }}
.result {{ margin-top:12px; padding:12px; border-radius:8px; font-size:14px; display:none; }}
.result.ok {{ display:block; background:#f6ffed; border:1px solid #b7eb8f; color:#52c41a; }}
.result.err {{ display:block; background:#fff2f0; border:1px solid #ffccc7; color:#e94560; }}
.back-btn {{ display:inline-block; margin-top:16px; padding:8px 24px; background:#f0f0f0; border:none; border-radius:8px; font-size:13px; color:#666; cursor:pointer; text-decoration:none; }}
</style>
</head>
<body>
<div class="card">
    <div style="font-size:40px;margin-bottom:8px;">📦</div>
    <h3 style="font-size:16px;color:#666;font-weight:400;">扫码报工</h3>
    <div class="order-id">{order_id}</div>
    <div id="stepList"></div>
    <div id="result" class="result"></div>
    <div style="font-size:11px;color:#bbb;margin-top:12px;">请选择要报工的工序</div>
</div>
<a class="back-btn" href="javascript:history.back()">← 返回</a>
<script>
const ORDER_ID = "{order_id}";
const WORKER = prompt("请输入你的姓名：", "");
if (!WORKER) {{ document.body.innerHTML = '<div style="text-align:center;padding:40px;color:#e94560;">❌ 需要姓名才能报工</div>'; }}

// 获取订单工序
fetch('/api/production_orders').then(r=>r.json()).then(data => {{
    const orders = data.orders || [];
    const order = orders.find(o => o.inner_id === ORDER_ID);
    const steps = order ? (order.flow || []) : [];
    const container = document.getElementById('stepList');
    if (steps.length === 0) {{
        container.innerHTML = '<div class="info">该订单暂无工序数据</div>';
        return;
    }}
    steps.forEach((s, i) => {{
        const done = s.done;
        const btn = document.createElement('button');
        btn.className = 'step-btn ' + (done ? 'btn-gray' : 'btn-primary');
        btn.textContent = (done ? '✅ ' : '') + s.step + (done ? ' (已完成)' : '');
        btn.disabled = done;
        if (!done) {{
            btn.onclick = () => submitReport(i, s.step);
        }}
        container.appendChild(btn);
    }});
}}).catch(e => {{
    document.getElementById('stepList').innerHTML = '<div class="info">加载失败: ' + e.message + '</div>';
}});

async function submitReport(stepIndex, stepName) {{
    const resultEl = document.getElementById('result');
    resultEl.className = 'result';
    resultEl.textContent = '提交中...';
    resultEl.style.display = 'block';
    try {{
        const res = await fetch('/api/scan_report', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{order_id: ORDER_ID, step: stepName, worker: WORKER}})
        }});
        const data = await res.json();
        if (data.success) {{
            resultEl.className = 'result ok';
            resultEl.textContent = '✅ ' + (data.message || '报工成功');
            // 刷新页面
            setTimeout(() => location.reload(), 1500);
        }} else {{
            resultEl.className = 'result err';
            resultEl.textContent = '❌ ' + (data.error || '报工失败');
        }}
    }} catch(e) {{
        resultEl.className = 'result err';
        resultEl.textContent = '❌ 网络错误: ' + e.message;
    }}
}}
</script>
</body>
</html>'''
    return html


# ==================== 1688开放平台集成 ====================

ALIBABA_CONFIG = {
    'app_key': 1452593,
    'app_secret': 'f4UOJ5NO1X',
    'access_token': 'bdb56a38-b85b-410d-acb2-74a04fc20496',
    'server': 'gw.open.1688.com'
}

def _1688_sign(url_path, params, secret):
    """1688签名：HMAC-SHA1"""
    param_list = sorted([str(k) + str(v) for k, v in params.items()])
    msg = url_path.encode('utf-8')
    for p in param_list:
        msg += p.encode('utf-8')
    sha = hmac.new(secret.encode('utf-8'), msg, hashlib.sha1)
    return sha.hexdigest().upper()

def _1688_api(api_uri, biz_params=None):
    """调用1688开放平台API"""
    cfg = ALIBABA_CONFIG
    url_path = f'param2/{api_uri}/{cfg["app_key"]}'
    params = {'access_token': cfg['access_token']}
    if biz_params:
        params.update(biz_params)
    params['_aop_signature'] = _1688_sign(url_path, params, cfg['app_secret'])
    url = f'https://{cfg["server"]}/openapi/{url_path}'
    form_data = urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, data=form_data.encode('utf-8'), method='POST')
        resp = urllib.request.urlopen(req, timeout=30)
        return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f'[1688API] {api_uri} 调用失败: {e}')
        return {}


def _1688_format_order(o):
    """格式化1688订单为统一格式"""
    info = o.get('baseInfo', {})
    items = o.get('productItems', [])
    product_list = []
    for item in items:
        product_list.append({
            'name': item.get('name', ''),
            'sku': item.get('productCargoNumber', ''),
            'qty': item.get('quantity', 0),
            'price': item.get('price', 0),
            'spec': item.get('skuInfos', [{'value': ''}])[0].get('value', ''),
            'skuId': item.get('skuID', ''),
            'productId': item.get('productID', '')
        })
    so_id = str(info.get('idOfStr', info.get('id', '')))
    return {
        'so_id': so_id,
        'platform': '1688',
        'order_status': info.get('status', ''),
        'status_label': '待发货' if info.get('status') == 'waitsellersend' else info.get('status', ''),
        'created': info.get('createTime', '')[:8] if info.get('createTime') else '',
        'pay_time': info.get('payTime', '')[:8] if info.get('payTime') else '',
        'total_amount': info.get('totalAmount', 0),
        'shipping_fee': info.get('shippingFee', 0) / 100,
        'discount': info.get('discount', 0) / 100,
        'receiver_name': info.get('receiverName', info.get('buyerLoginId', '')),
        'receiver_mobile': info.get('receiverMobile', ''),
        'receiver_address': info.get('receiverAddress', ''),
        'receiver_phone': info.get('receiverPhone', ''),
        'shop_name': info.get('buyerLoginId', '1688'),
        'items': product_list,
        'buyer_login_id': info.get('buyerLoginId', ''),
        'alipay_trade_id': info.get('alipayTradeId', ''),
        'trade_type': info.get('tradeType', ''),
        'buyer_memo': '',
        'seller_memo': get_order_memo(so_id),
    }

# ==================== 订单备注本地存储 ====================

_ORDER_MEMO = {}

def get_order_memo(so_id):
    return _ORDER_MEMO.get(so_id, '')

def set_order_memo(so_id, memo):
    _ORDER_MEMO[so_id] = memo

@app.route('/api/order/1688-memo', methods=['POST'])
def api_order_1688_memo():
    """修改卖家备注并同步回1688"""
    if 'username' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401
    data = request.get_json() or {}
    so_id = data.get('so_id', '')
    memo = data.get('memo', '')
    if not so_id:
        return jsonify({'success': False, 'error': '缺少订单ID'})
    # 先本地存储
    set_order_memo(so_id, memo)
    # 同步到1688
    try:
        # 调用1688 memoAdd API
        result = _1688_api('1/com.alibaba.trade/alibaba.order.memoAdd', {
            'orderId': so_id,
            'memo': memo,
            'remarkIcon': '0'
        })
        if result.get('errorCode') or result.get('errorMessage'):
            return jsonify({'success': False, 'error': f'1688同步失败: {result.get("errorMessage", result.get("errorCode", "未知错误"))}', 'local_saved': True})
    except Exception as e:
        return jsonify({'success': True, 'error': f'1688同步失败: {str(e)}', 'local_saved': True})
    return jsonify({'success': True, 'message': '备注已保存并同步到1688'})

@app.route('/api/realtime/orders', methods=['GET'])
def api_realtime_orders():
    """获取所有实时订单（从本地缓存读取，毫秒级返回）"""
    import time as _t

    shop_config = load_shop_config()

    # 先尝试读本地缓存
    try:
        if os.path.exists(ORDERS_CACHE_FILE):
            with open(ORDERS_CACHE_FILE, 'r', encoding='utf-8') as f:
                cache = json.load(f)
                cached_orders = cache.get('orders', [])
            if cached_orders:
                try:
                    import order_sync as _osync
                    for o in cached_orders:
                        o['shop_name'] = _osync.normalize_shop_display(o.get('shop_name', ''))
                except ImportError:
                    pass
                cached_orders.sort(key=lambda x: x.get('created', ''), reverse=True)
                print(f'[实时订单] 缓存命中: {len(cached_orders)} 条订单')
                return jsonify({
                    'success': True,
                    'total': len(cached_orders),
                    'orders': cached_orders,
                    'platforms': list(set(o.get('platform', '1688') for o in cached_orders)),
                    'shop_config': shop_config,
                    'cache_status': 'hit'
                })
    except Exception as e:
        print(f'[实时订单] 读缓存失败: {e}')

    # 缓存不存在或为空，返回空，不等1688
    print('[实时订单] 缓存未命中，返回空（后台正在同步）')
    return jsonify({
        'success': True,
        'total': 0,
        'orders': [],
        'platforms': [],
        'shop_config': shop_config,
        'cache_status': 'empty'
    })

# ==================== 店铺客服配置 API ====================

SHOP_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'shop_config.json')

DEFAULT_SHOP_CONFIG = [
    {"id": "shop_1688_1", "platform": "1688", "shop_name": "友尚", "customer_service": "张慧平,戴志美", "sort_order": 1},
    {"id": "shop_1688_2", "platform": "1688", "shop_name": "亚润", "customer_service": "陈贝贝", "sort_order": 2},
    {"id": "shop_1688_3", "platform": "1688", "shop_name": "三羊", "customer_service": "罗怡", "sort_order": 3},
    {"id": "shop_1688_4", "platform": "1688", "shop_name": "正方形", "customer_service": "周井梅", "sort_order": 4},
    {"id": "shop_1688_5", "platform": "1688", "shop_name": "大鱼", "customer_service": "周井梅", "sort_order": 5},
    {"id": "shop_1688_6", "platform": "1688", "shop_name": "新鑫星", "customer_service": "戴志美", "sort_order": 6},
    {"id": "shop_tmall_1", "platform": "tmall", "shop_name": "飞机盒彩色专卖店", "customer_service": "廖思美", "sort_order": 7},
    {"id": "shop_tmall_2", "platform": "tmall", "shop_name": "飞机盒正方形专卖店", "customer_service": "廖思美", "sort_order": 8},
    {"id": "shop_tmall_3", "platform": "tmall", "shop_name": "飞机盒止合专卖店", "customer_service": "石梅清", "sort_order": 9},
    {"id": "shop_tmall_4", "platform": "tmall", "shop_name": "飞机盒扣底盒专卖店", "customer_service": "石梅清", "sort_order": 10},
    {"id": "shop_tmall_5", "platform": "tmall", "shop_name": "飞机盒小批量专卖店", "customer_service": "张文杰", "sort_order": 11},
    {"id": "shop_taobao_1", "platform": "taobao", "shop_name": "飞机盒品牌店", "customer_service": "张文杰", "sort_order": 12},
    {"id": "shop_taobao_2", "platform": "taobao", "shop_name": "俊鑫纸品厂", "customer_service": "石梅清", "sort_order": 13},
    {"id": "shop_taobao_3", "platform": "taobao", "shop_name": "当下家包装", "customer_service": "张文杰", "sort_order": 14}
]

def load_shop_config():
    if not os.path.exists(SHOP_CONFIG_FILE):
        save_shop_config(DEFAULT_SHOP_CONFIG)
        return list(DEFAULT_SHOP_CONFIG)
    try:
        with open(SHOP_CONFIG_FILE, 'r') as f:
            return json.load(f)
    except:
        return list(DEFAULT_SHOP_CONFIG)

def save_shop_config(config):
    with open(SHOP_CONFIG_FILE, 'w') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

@app.route('/api/shop-config', methods=['GET'])
def api_get_shop_config():
    config = load_shop_config()
    return jsonify({'success': True, 'config': config})

@app.route('/api/shop-config', methods=['POST'])
def api_save_shop_config():
    try:
        data = request.get_json(force=True) or {}
        config = data.get('config', [])
        save_shop_config(config)
        return jsonify({'success': True, 'message': '保存成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/shop-config/reset', methods=['POST'])
def api_reset_shop_config():
    save_shop_config(DEFAULT_SHOP_CONFIG)
    return jsonify({'success': True, 'config': list(DEFAULT_SHOP_CONFIG)})


# ========== 后台定时同步订单（快麦 ERP）==========
ORDERS_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'orders_cache.json')


def _km_sync_orders_to_cache(days_back=14):
    import order_sync as _osync
    r = _osync.sync_orders_to_cache(
        ORDERS_CACHE_FILE,
        days_back=days_back,
        memo_getter=get_order_memo,
        include_1688_direct=True,
    )
    return r.get('pending_count', 0)


def _sync_orders_task():
    """后台线程：从快麦拉订单存到本地缓存"""
    import time as _t
    while True:
        try:
            _km_sync_orders_to_cache(days_back=14)
        except Exception as ex:
            print(f'[订单同步] 错误: {ex}')
        _t.sleep(300)

@app.route('/api/sync/force', methods=['POST'])
def api_sync_force():
    if not resolve_login_user():
        return jsonify({'success': False, 'error': '未登录'}), 401
    import order_sync as _osync
    ok, msg = _osync.start_force_sync_async(
        ORDERS_CACHE_FILE,
        days_back=30,
        memo_getter=get_order_memo,
        include_1688_direct=True,
    )
    if not ok:
        return jsonify({'success': False, 'error': msg}), 409
    return jsonify({'success': True, 'async': True, 'message': msg})


@app.route('/api/sync/status', methods=['GET'])
def api_sync_status():
    if not resolve_login_user():
        return jsonify({'success': False, 'error': '未登录'}), 401
    import order_sync as _osync
    st = _osync.force_sync_status()
    last = st.get('last') or {}
    return jsonify({
        'success': True,
        'running': st.get('running'),
        'error': st.get('error'),
        'phase': st.get('phase'),
        'detail': st.get('detail'),
        'last': last,
        'count': last.get('pending_count') if isinstance(last, dict) else None,
    })


@app.route('/api/km/probe', methods=['GET'])
def api_km_probe():
    if 'username' not in session:
        return jsonify({'success': False, 'error': '未登录'}), 401
    import km_api as _km
    return jsonify({'success': True, 'data': _km.km_probe()})


import threading as _th
_sync_thread = _th.Thread(target=_sync_orders_task, daemon=True)
_sync_thread.start()
print('[订单同步] 快麦+1688 后台同步已启动（每5分钟）')

# ==================== 打单管理 API ====================

@app.route('/api/production/dashboard')
def production_dashboard():
    """打单管理：订单列表+打印状态+筛选"""
    # 读取打印日志
    printed_set = set()
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT order_id, created_at, printed_by FROM print_logs WHERE status='printed'")
        for r in cur.fetchall():
            printed_set.add((r['order_id'], r['created_at'], r['printed_by'] or ''))
        cur.close()
        db.close()
    except:
        pass
    printed_ids = {p[0] for p in printed_set}
    printed_info = {p[0]: {'time': p[1], 'by': p[2]} for p in printed_set}
    
    # 读取工单
    flow_map = {}
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT * FROM production_flows")
        for r in cur.fetchall():
            flow_map[r['order_id']] = r
        cur.close()
        db.close()
    except:
        pass
    
    # 加载全部库存用于现货判定
    inventory_data = load_inventory()
    inventory_list = inventory_data.get('finished', [])
    
    def match_inventory(spec_str, spec_name, need_qty):
        """根据规格参数匹配库存"""
        spec = spec_str or ''
        dim_m = re.search(r'(\d+[\.\d]*)\s*[*×xX]\s*(\d+[\.\d]*)', spec)
        if not dim_m:
            return False, 0, '无法解析尺寸'
        l, w = float(dim_m.group(1)), float(dim_m.group(2))
        h_m = re.search(r'(?:高|高度)[【】]?(\d+[\.\d]*)', spec)
        if not h_m:
            h_m = re.search(r'(\d+[\.\d]*)cm高', spec)
        h = float(h_m.group(1)) if h_m else 0
        best_qty = 0
        best_name = ''
        for inv in inventory_list:
            inv_l = float(inv.get('length', 0) or 0)
            inv_w = float(inv.get('width', 0) or 0)
            inv_h = float(inv.get('height', 0) or 0)
            inv_qty = int(inv.get('qty', 0) or 0)
            if abs(inv_l - l) <= 0.5 and abs(inv_w - w) <= 0.5:
                if h == 0 or abs(inv_h - h) <= 0.5:
                    if inv_qty > best_qty:
                        best_qty = inv_qty
                        best_name = inv.get('name', '')
        if best_qty > 0:
            return best_qty >= need_qty, best_qty, f'{best_name} 库存{best_qty}'
        return False, 0, '无匹配库存'
    
    # 加载材料映射
    qd = load_quote_data()
    material_mapping = qd.get('material_mapping', []) if qd else []
    
    def match_material(name_str):
        """根据商品名匹配材料名"""
        name_low = (name_str or '').lower()
        for m in material_mapping:
            kw_list = [k.strip().lower() for k in (m.get('keywords', '') or '').split(',') if k.strip()]
            for kw in kw_list:
                if kw and kw in name_low:
                    return m.get('material_name', kw)
        return '—'
    
    # 读取订单缓存
    all_orders = []
    try:
        cache_file = ORDERS_CACHE_FILE
        if not os.path.isabs(cache_file):
            cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), cache_file)
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            all_orders = cache.get('orders', [])
    except:
        pass
    
    shops = set()
    product_types = set()
    
    result = []
    for o in all_orders:
        so_id = o.get('so_id', '')
        first_item = (o.get('items') or [{}])[0]
        prod_name = first_item.get('name', '')
        order_type = '飞机盒'
        if '纸箱' in prod_name: order_type = '纸箱'
        elif '扣底盒' in prod_name or '双插盒' in prod_name: order_type = '扣底盒'
        elif '现货' in prod_name or '现' in prod_name: order_type = '现货'
        
        try:
            import order_sync as _osync
            shop = _osync.normalize_shop_display(o.get('shop_name', '') or '')
        except ImportError:
            shop = (o.get('shop_name') or '').strip() or '未知店铺'
        created_date = (o.get('created') or '')[:10]
        
        shops.add(shop)
        product_types.add(order_type)
        
        flow = flow_map.get(so_id)
        has_flow = flow is not None
        
        progress = 0
        steps = []
        if flow:
            try:
                steps_list = json.loads(flow['steps_json']) if isinstance(flow['steps_json'], str) else flow['steps_json']
            except:
                steps_list = []
            current_idx = flow.get('current_step_index', 0) or 0
            total_s = flow.get('total_steps', 0) or len(steps_list)
            progress = round(current_idx / total_s * 100) if total_s > 0 else 0
            for i, s in enumerate(steps_list):
                sname = s['name'] if isinstance(s, dict) else s
                done = i < current_idx
                steps.append({"name": sname, "done": done, "active": i == current_idx})
        
        total_qty = sum(i.get('qty', 0) for i in (o.get('items') or []))
        addr = o.get('receiver_address', '')
        addr_parts = addr.split() if addr else []
        province = addr_parts[0] if len(addr_parts) > 0 else ''
        
        specs = []
        full_items = []
        for item in (o.get('items') or []):
            spec = item.get('spec', '') or ''
            qty = item.get('qty', 0) or 0
            sku = item.get('sku', '') or ''
            specs.append({'spec': spec, 'qty': qty})
            # 库存判定
            has_stock, stock_qty, stock_info = match_inventory(spec, item.get('name', ''), qty)
            full_items.append({
                'name': item.get('name', '') or '',
                'spec': spec,
                'qty': qty,
                'sku': sku,
                'skuId': item.get('skuId', '') or '',
                'has_stock': has_stock,
                'stock_qty': stock_qty,
                'stock_info': stock_info,
                'material_name': match_material(item.get('name', ''))
            })
        
        is_printed = so_id in printed_ids
        pi = printed_info.get(so_id, {})
        
        # 整单级库存判定：全部有货还是部分有货
        has_all_stock = all(item.get('has_stock', False) for item in full_items)
        
        result.append({
            "so_id": so_id,
            "shop": shop,
            "province": province,
            "created": created_date,
            "product_name": prod_name,
            "product_type": order_type,
            "specs": specs,
            "full_items": full_items,
            "qty": total_qty,
            "seller_memo": o.get('seller_memo', '') or '',
            "buyer_memo": o.get('buyer_memo', '') or '',
            "printed": is_printed,
            "printed_at": pi.get('time', ''),
            "printed_by": pi.get('by', ''),
            "has_flow": has_flow,
            "flow_status": flow.get('status', '') if flow else '',
            "receiver": o.get('receiver_name', ''),
            "address": o.get('receiver_address', ''),
            "phone": o.get('receiver_phone', '') or o.get('receiver_mobile', ''),
            "progress": progress,
            "steps": steps,
            "has_all_stock": has_all_stock,
        })
    
    result.sort(key=lambda x: x['created'], reverse=True)
    
    return jsonify({
        "success": True,
        "orders": result,
        "filters": {
            "shops": sorted(shops),
            "types": sorted(product_types)
        },
        "material_mapping": load_quote_data().get('material_mapping', []) if load_quote_data() else []
    })

@app.route('/api/production/print_log', methods=['POST'])
def production_print_log():
    """记录打印日志"""
    data = request.get_json() or {}
    order_id = data.get('order_id', '')
    shop_name = data.get('shop_name', '')
    product_type = data.get('product_type', '')
    printed_by = data.get('printed_by', '')
    if not order_id:
        return jsonify({'success': False, 'error': '缺少order_id'})
    try:
        db = get_db()
        cur = db.cursor()
        # 先删除旧记录
        cur.execute("DELETE FROM print_logs WHERE order_id=%s AND status='printed'", (order_id,))
        cur.execute("INSERT INTO print_logs (order_id, shop_name, product_type, printed_by, status) VALUES (%s,%s,%s,%s,'printed')",
                    (order_id, shop_name, product_type, printed_by))
        db.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/production/print_log/<order_id>', methods=['DELETE'])
def production_unmark_print(order_id):
    """取消打印标记"""
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute("DELETE FROM print_logs WHERE order_id=%s AND status='printed'", (order_id,))
        db.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/production/print')
def production_print():
    """打印工单（跳转原生打印）"""
    ids = request.args.get('ids', '')
    sku_id = request.args.get('sku_id', '')
    
    html = '<html><head><meta charset="utf-8"><style>body{font-family:monospace;font-size:12px;padding:20px;}h2{text-align:center;}table{width:100%;border-collapse:collapse;margin-top:12px;}th,td{border:1px solid #ccc;padding:6px 8px;text-align:left;font-size:11px;}th{background:#f0f0f0;}.label{font-weight:600;color:#333;}.value{color:#555;}</style></head><body>'
    
    if sku_id:
        # 按单规格打印
        order_id = ids
        try:
            cache_file = ORDERS_CACHE_FILE
            if not os.path.isabs(cache_file):
                cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), cache_file)
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                for o in cache.get('orders', []):
                    if o.get('so_id') == order_id:
                        for item in (o.get('items') or []):
                            if item.get('skuId', '') == sku_id:
                                name = item.get('name', '')
                                spec = item.get('spec', '')
                                qty = item.get('qty', 0)
                                sku = item.get('sku', '')
                                html += f'<h2>📋 规格工单</h2>'
                                html += f'<p><span class="label">订单号：</span><span class="value">{order_id}</span></p>'
                                html += f'<p><span class="label">商品：</span><span class="value">{name}</span></p>'
                                html += f'<p><span class="label">规格：</span><span class="value">{spec}</span></p>'
                                html += f'<p><span class="label">数量：</span><span class="value">{qty}</span></p>'
                                if sku:
                                    html += f'<p><span class="label">SKU：</span><span class="value">{sku}</span></p>'
                                break
                        break
        except:
            pass
        if html == '<html><head><meta charset="utf-8"><style>body{font-family:monospace;font-size:12px;padding:20px;}h2{text-align:center;}table{width:100%;border-collapse:collapse;margin-top:12px;}th,td{border:1px solid #ccc;padding:6px 8px;text-align:left;font-size:11px;}th{background:#f0f0f0;}.label{font-weight:600;color:#333;}.value{color:#555;}</style></head><body>':
            html += '<p style="color:#e94560;">未找到该规格</p>'
    else:
        # 整单打印（原有逻辑）
        html += '<h2>📋 生产工单</h2>'
        html += f'<p>订单号: {ids}</p>'
        html += '<p>请使用浏览器打印功能 (Ctrl+P)</p>'
    
    html += '<script>window.print();</script></body></html>'
    return html

@app.route('/api/flow/create', methods=['POST'])
def production_flow_create():
    """创建生产工单"""
    data = request.get_json() or {}
    order_id = data.get('order_id', '')
    if not order_id:
        return jsonify({'success': False, 'error': '缺少order_id'})
    try:
        db = get_db()
        cur = db.cursor()
        # 检查是否已存在
        cur.execute("SELECT * FROM production_flows WHERE order_id=%s", (order_id,))
        existing = cur.fetchone()
        if existing:
            # 重置已有工单
            cur.execute("UPDATE production_flows SET current_step_index=0, status='active', updated_at=NOW() WHERE order_id=%s", (order_id,))
            db.close()
            return jsonify({'success': True, 'flow': {'order_id': order_id, 'status': 'active'}, 'message': '工单已重置'})
        
        # 读取订单类型
        order_type = '飞机盒'
        try:
            cache_file = ORDERS_CACHE_FILE
            if not os.path.isabs(cache_file):
                cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), cache_file)
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                for o in cache.get('orders', []):
                    if o.get('so_id') == order_id:
                        fn = ((o.get('items') or [{}])[0]).get('name', '')
                        if '纸箱' in fn: order_type = '纸箱'
                        elif '扣底盒' in fn or '双插盒' in fn: order_type = '扣底盒'
                        elif '现货' in fn or '现' in fn: order_type = '现货'
                        break
        except:
            pass
        
        # 工单步骤
        steps_map = {
            '飞机盒': ['接单', '啤货', '印刷', '裱纸', '模切', '贴胶', '成型', '质检', '打包', '发货'],
            '纸箱': ['接单', '啤货', '印刷', '裱纸', '模切', '开槽', '打钉', '质检', '打包', '发货'],
            '扣底盒': ['接单', '啤货', '印刷', '裱纸', '模切', '贴胶', '成型', '质检', '打包', '发货'],
            '现货': ['接单', '捡货', '质检', '打包', '发货'],
        }
        steps = steps_map.get(order_type, ['接单', '生产', '发货'])
        total = len(steps)
        
        # 啤货推荐
        machine_recommend = ''
        
        cur.execute(
            "INSERT INTO production_flows (id, order_id, product_type, steps_json, current_step_index, total_steps, status, machine_recommend) VALUES (%s,%s,%s,%s,0,%s,'active',%s)",
            (order_id, order_id, order_type, json.dumps(steps, ensure_ascii=False), total, machine_recommend)
        )
        db.close()
        return jsonify({'success': True, 'flow': {'order_id': order_id, 'product_type': order_type, 'total_steps': total, 'machine_recommend': machine_recommend}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/flow/step', methods=['POST'])
def production_flow_step():
    """推进/回退工单工序"""
    data = request.get_json() or {}
    order_id = data.get('order_id', '')
    action = data.get('action', 'next')  # next/prev
    if not order_id:
        return jsonify({'success': False, 'error': '缺少order_id'})
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT * FROM production_flows WHERE order_id=%s", (order_id,))
        flow = cur.fetchone()
        if not flow:
            return jsonify({'success': False, 'error': '工单不存在'})
        idx = flow['current_step_index'] or 0
        total = flow['total_steps'] or len(json.loads(flow['steps_json']) if isinstance(flow['steps_json'], str) else flow['steps_json'])
        if action == 'next' and idx < total - 1:
            idx += 1
        elif action == 'prev' and idx > 0:
            idx -= 1
        status = 'active' if idx < total - 1 else 'done'
        cur.execute("UPDATE production_flows SET current_step_index=%s, status=%s, updated_at=NOW() WHERE order_id=%s", (idx, status, order_id))
        db.close()
        return jsonify({'success': True, 'current_step_index': idx, 'status': status, 'total_steps': total})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    print("🏭 飞机盒智能生产管理系统启动中...")
    print("📡 http://0.0.0.0:3002")
    app.run(host='0.0.0.0', port=3002, threaded=True)
