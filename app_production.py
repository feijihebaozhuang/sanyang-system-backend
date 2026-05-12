#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞机盒智能生产管理系统 - 后端API
小马哥专属
"""

from flask import Flask, jsonify, send_from_directory, request, make_response, Response, session
from flask_cors import CORS
import json, datetime, csv, io, os, hashlib, copy, time, re, hmac, urllib.parse, urllib.request
from pypinyin import lazy_pinyin
import pymysql

from settings import ALIBABA_CONFIG, ALIBABA_SHOPS, DB_CONFIG, FLASK_SECRET_KEY

def get_db():
    """获取数据库连接，每次调用新建（线程安全）"""
    return pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)

app = Flask(__name__, static_folder='.')
app.secret_key = FLASK_SECRET_KEY
CORS(app, supports_credentials=True)

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

def load_data():
    """从MySQL加载持久化数据"""
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
        "users": default_users,
        "employee_status": {},
        "permission_data": {
            "processes": [
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
            "employee_enabled": {},
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
                "戴雅利": {"首页": True, "订单生产进度": True, "扫码报工": True, "日报表": True, "数据看板": True, "刀模": True, "库存": True, "聚水潭": True, "员工": True, "权限管理": True, "报价": True},
                "邓涛": {"首页": True, "订单生产进度": True, "扫码报工": True, "日报表": True, "数据看板": True, "刀模": True, "库存": True, "聚水潭": True, "员工": True, "权限管理": False, "报价": False},
                "李周海": {"首页": True, "订单生产进度": True, "扫码报工": True, "日报表": True, "员工": True, "刀模": False, "库存": False, "聚水潭": False, "数据看板": False, "权限管理": False, "报价": False},
            }
        }
    }
    try:
        db = get_db()
        cur = db.cursor()
        # 从users表读取
        cur.execute("SELECT username, password, display_name, role, employee_name, enabled FROM users")
        rows = cur.fetchall()
        users = {}
        for r in rows:
            users[r['username']] = {
                'password': r['password'],
                'name': r['display_name'] or r['username'],
                'role': r['role'] or '员工',
                'employee_name': r['employee_name'] or ''
            }
        # 从employees表读取
        cur.execute("SELECT name, position, enabled FROM employees")
        emp_rows = cur.fetchall()
        employees = [{'name': r['name'], 'position': r['position'] or ''} for r in emp_rows]
        employee_enabled = {}
        for r in emp_rows:
            employee_enabled[r['name']] = bool(r['enabled'])

        # 从employee_permissions表读取
        cur.execute("SELECT employee_name, permission_key, enabled FROM employee_permissions")
        perm_rows = cur.fetchall()
        permission_map = {}
        all_perm_keys = set()
        for r in perm_rows:
            en = r['employee_name']
            pk = r['permission_key']
            val = bool(r['enabled'])
            all_perm_keys.add(pk)
            if en not in permission_map:
                permission_map[en] = {}
            permission_map[en][pk] = val

        # 构建permissions字典
        permissions = {}
        for emp in employees:
            en = emp['name']
            perms = permission_map.get(en, {})
            permissions[en] = {pk: perms.get(pk, False) for pk in sorted(all_perm_keys)}

        # 从order_extras表读取
        cur.execute("SELECT so_id, urgent FROM order_extras")
        extra_rows = cur.fetchall()
        order_extra = {}
        for r in extra_rows:
            order_extra[r['so_id']] = {'urgent': bool(r['urgent'])}

        cur.close()
        db.close()

        result = {
            'users': users,
            'employee_status': {},
            'order_extra': order_extra,
            'permission_data': {
                'processes': default['permission_data']['processes'],
                'positions': default['permission_data']['positions'],
                'employees': employees,
                'permissions': permissions,
                'employee_enabled': employee_enabled
            },
            'resigned_employees': []
        }
        return result
    except Exception as e:
        print(f'[MySQL load_data] 错误: {e}')
        return default

def save_data(data):
    """保存数据到MySQL"""
    try:
        db = get_db()
        cur = db.cursor()
        # 保存users
        users = data.get('users', {})
        for uid, uinfo in users.items():
            if uid == 'admin' and uinfo.get('is_system'):
                continue  # 不覆盖系统admin
            cur.execute(
                "INSERT INTO users (username, password, display_name, role, employee_name, enabled) VALUES (%s,%s,%s,%s,%s,1) ON DUPLICATE KEY UPDATE password=VALUES(password), display_name=VALUES(display_name), role=VALUES(role), employee_name=VALUES(employee_name)",
                (uid, uinfo.get('password',''), uinfo.get('name',uid), uinfo.get('role','员工'), uinfo.get('employee_name',''))
            )

        # 保存employees
        emp_list = data.get('permission_data', {}).get('employees', [])
        for emp in emp_list:
            name = emp.get('name', '')
            pos = emp.get('position', '')
            cur.execute(
                "INSERT INTO employees (name, position, enabled) VALUES (%s,%s,1) ON DUPLICATE KEY UPDATE position=VALUES(position)",
                (name, pos)
            )

        # 保存employee_permissions
        perms = data.get('permission_data', {}).get('permissions', {})
        for emp_name, perm_dict in perms.items():
            for pk, val in perm_dict.items():
                cur.execute(
                    "INSERT INTO employee_permissions (employee_name, permission_key, enabled) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE enabled=VALUES(enabled)",
                    (emp_name, pk, 1 if val else 0)
                )

        # 保存employee_enabled
        emp_enabled = data.get('permission_data', {}).get('employee_enabled', {})
        for name, enabled in emp_enabled.items():
            cur.execute(
                "UPDATE employees SET enabled=%s WHERE name=%s",
                (1 if enabled else 0, name)
            )

        # 保存order_extras
        order_extra = data.get('order_extra', {})
        for so_id, info in order_extra.items():
            urgent = 1 if info.get('urgent') else 0
            cur.execute(
                "INSERT INTO order_extras (so_id, urgent) VALUES (%s,%s) ON DUPLICATE KEY UPDATE urgent=VALUES(urgent)",
                (so_id, urgent)
            )

        cur.close()
        db.close()
        return True
    except Exception as e:
        print(f'[MySQL save_data] 错误: {e}')
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
    
    session['username'] = username
    session['user_name'] = user['name']
    session['role'] = user['role']
    session['employee_name'] = user['employee_name']
    
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
    """今日订单 - 从1688订单缓存读取真实数据"""
    date = request.args.get('date', datetime.date.today().strftime('%Y-%m-%d'))
    today_str = date.replace('-', '')
    
    # 店铺映射（1688店铺名 → 系统内显示名 + 客服）
    SHOP_NAME_MAP = {
        '三羊包装': {'store': '深圳三羊', 'worker': '罗怡'},
        '友尚包装': {'store': '深圳友尚', 'worker': '张慧平'},
        '正方形包装': {'store': '深圳正方形', 'worker': '周井梅'},
        '大鱼包装': {'store': '深圳大鱼', 'worker': '周井梅'},
        '亚润': {'store': '深圳亚润', 'worker': '陈贝贝'},
    }
    
    # 读取订单缓存
    orders = []
    try:
        if os.path.exists(ORDERS_CACHE_FILE):
            with open(ORDERS_CACHE_FILE, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            raw_orders = cache.get('orders', [])
            # 筛选今天的订单
            today_orders_raw = [o for o in raw_orders if o.get('created', '').startswith(today_str)]
            
            for o in today_orders_raw:
                shop_1688 = o.get('shop_name', '')
                shop_info = SHOP_NAME_MAP.get(shop_1688, {'store': shop_1688, 'worker': ''})
                items = o.get('items', [])
                product_names = '; '.join([f"{i.get('name','?')[:20]} x{i.get('qty',0)}" for i in items[:2]])
                if len(items) > 2:
                    product_names += f' …等{len(items)}种'
                
                orders.append({
                    'id': o.get('so_id', ''),
                    'store': shop_info['store'],
                    'worker': shop_info['worker'],
                    'product': product_names[:50] if product_names else (items[0].get('name','?')[:30] if items else '？'),
                    'qty': sum(i.get('qty', 0) for i in items),
                    'process': '待处理',
                    'status': '待发货',
                    'urgent': False,
                    'remark': o.get('seller_memo', '') or o.get('buyer_memo', ''),
                })
    except Exception as e:
        print(f'[今日订单] 读取缓存失败: {e}')
    
    return jsonify({
        'date': date,
        'summary': {
            'total_orders': len(orders),
            'in_production': len([o for o in orders if o['status'] not in ('已完成',)]),
            'urgent_orders': len([o for o in orders if o['urgent']]),
            'completed': len([o for o in orders if o['status'] == '已完成']),
        },
        'today_orders': orders
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

# ==================== 搜索订单 ====================
@app.route('/api/search_order')
def search_order():
    query = request.args.get('q', '')
    if not query:
        return jsonify({"found": False, "message": "请输入单号"})
    # 从持久化数据读取加急状态
    saved = _order_extra.get(query, {})
    return jsonify({
        "found": True,
        "order_id": query,
        "urgent": saved.get("urgent", False),
        "production_status": {
            "status": "生产中",
            "current_process": "啤机",
            "diemold": "DM-001",
            "progress": 65,
            "steps": [
                {"name": "审单", "done": True, "time": "2026-04-26 08:30"},
                {"name": "算料", "done": True, "time": "2026-04-26 09:00"},
                {"name": "分纸", "done": True, "time": "2026-04-26 09:30"},
                {"name": "啤机", "done": False, "time": "进行中"},
                {"name": "清废", "done": False, "time": "-"},
                {"name": "打包", "done": False, "time": "-"},
                {"name": "发货", "done": False, "time": "-"},
            ]
        },
        "jst_detail": {
            "order_id": query,
            "store": "友尚旗舰店",
            "customer": "广州xx电子",
            "product": "飞机盒30*20*15",
            "qty": 500,
            "amount": 1250.00,
            "order_date": "2026-04-26",
            "delivery_date": "2026-04-28",
            "address": "广东省广州市番禺区xx工业区xx号",
            "logistics": "顺丰快递",
        }
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
        # 洋坑塘默认：客服权限——查看订单/聚水潭/库存，不涉及生产
        default_funcs = {
            '聚水潭': True, '订单': True, '订单备注': True, '库存': True,
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
PERM_FEATURES = ["首页","订单生产进度","扫码报工","日报表","数据看板","刀模","库存","原材料","聚水潭","员工","权限管理","报价","实时订单"]

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

def load_quote_data():
    """从MySQL加载报价配置"""
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT config_key, config_value FROM quote_config")
        rows = cur.fetchall()
        cur.close()
        db.close()
        result = {}
        for r in rows:
            key = r['config_key']
            val = r['config_value']
            if isinstance(val, str):
                try:
                    val = json.loads(val)
                except:
                    pass
            result[key] = val
        if not result:
            return None
        return result
    except Exception as e:
        print(f'[MySQL load_quote_data] 错误: {e}')
        return None

def save_quote_data(qd):
    """保存报价配置到MySQL"""
    try:
        db = get_db()
        cur = db.cursor()
        for key, val in qd.items():
            cur.execute(
                "INSERT INTO quote_config (config_key, config_value) VALUES (%s,%s) ON DUPLICATE KEY UPDATE config_value=VALUES(config_value)",
                (key, json.dumps(val, ensure_ascii=False))
            )
        cur.close()
        db.close()
        return True
    except Exception as e:
        print(f'[MySQL save_quote_data] 错误: {e}')
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

# ==================== 静态文件 ====================
@app.route('/')
def index():
    resp = make_response(send_from_directory('.', 'index_production.html'))
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

def _1688_fetch_orders(page=1, pagesize=50):
    """获取1688待发货订单（从当前配置的单店拉取，最多8页）"""
    api = '1/com.alibaba.trade/alibaba.trade.getSellerOrderList'
    all_orders = []
    current_page = page
    max_pages = 8
    _tok = ALIBABA_CONFIG.get("access_token") or ""
    _tok_preview = (_tok[:12] + "…") if len(_tok) > 12 else _tok
    print(f'[1688] 拉取订单: 店铺={ALIBABA_CONFIG.get("shop_name","默认")}, token={_tok_preview!r}')

    while current_page <= max_pages:
        result = _1688_api(api, {
            'page': current_page,
            'pageSize': pagesize
        })
        orders = result.get('result', [])
        if not orders:
            break
        all_orders.extend(orders)
        if len(orders) < pagesize:
            break
        current_page += 1
    return all_orders


def _1688_fetch_all_shops_orders():
    """遍历所有1688店铺，拉取每个店铺的订单并合并（独立函数，不依赖全局配置）"""
    import time as _t
    api = '1/com.alibaba.trade/alibaba.trade.getSellerOrderList'
    all_shop_orders = []
    max_pages = 3  # 最多翻3页

    for shop in ALIBABA_SHOPS:
        shop_name = shop['shop_name']
        token = shop['access_token']
        app_key = int(shop['app_key'])
        app_secret = shop['app_secret']
        server = shop['server']
        print(f'[1688] 拉取店铺: {shop_name}')
        for page in range(1, max_pages + 1):
            try:
                url_path = f'param2/{api}/{app_key}'
                params = {'access_token': token, 'page': page, 'pageSize': 50}
                param_list = sorted([str(k) + str(v) for k, v in params.items()])
                msg = url_path.encode('utf-8')
                for p in param_list:
                    msg += p.encode('utf-8')
                sign = hmac.new(app_secret.encode('utf-8'), msg, hashlib.sha1).hexdigest().upper()
                params['_aop_signature'] = sign
                url = f'https://{server}/openapi/{url_path}'
                form_data = urllib.parse.urlencode(params)
                req = urllib.request.Request(url, data=form_data.encode('utf-8'), method='POST')
                resp = urllib.request.urlopen(req, timeout=30)
                data = json.loads(resp.read().decode('utf-8'))
                orders = data.get('result', [])
                if not orders:
                    break
                for o in orders:
                    info = o.get('baseInfo', {})
                    info['shop_name'] = shop_name
                all_shop_orders.extend(orders)
                if len(orders) < 50:
                    break
                _t.sleep(0.5)
            except Exception as e:
                print(f'[1688] {shop_name} 第{page}页失败: {e}')
                break
        print(f'[1688] {shop_name}: 拉取完成')
    return all_shop_orders

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
        'shop_name': info.get('shop_name', info.get('buyerLoginId', '1688')),
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


def load_shop_config():
    """从MySQL加载店铺配置"""
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT id, shop_name, platform, customer_service, sort_order FROM shop_config ORDER BY sort_order ASC")
        rows = cur.fetchall()
        cur.close()
        db.close()
        if not rows:
            save_shop_config(list(DEFAULT_SHOP_CONFIG))
            return list(DEFAULT_SHOP_CONFIG)
        result = []
        for r in rows:
            result.append({
                'id': r['id'],
                'shop_name': r['shop_name'] or '',
                'platform': r['platform'] or '',
                'customer_service': r['customer_service'] or '',
                'sort_order': r['sort_order'] or 0
            })
        return result
    except Exception as e:
        print(f'[MySQL load_shop_config] 错误: {e}')
        return list(DEFAULT_SHOP_CONFIG)

def save_shop_config(config):
    """保存店铺配置到MySQL（truncate+批量insert）"""
    try:
        db = get_db()
        cur = db.cursor()
        cur.execute("TRUNCATE TABLE shop_config")
        for item in config:
            cur.execute(
                "INSERT INTO shop_config (id, shop_name, platform, customer_service, sort_order) VALUES (%s,%s,%s,%s,%s)",
                (
                    item.get('id', ''),
                    item.get('shop_name', ''),
                    item.get('platform', ''),
                    item.get('customer_service', ''),
                    item.get('sort_order', 0)
                )
            )
        cur.close()
        db.close()
        return True
    except Exception as e:
        print(f'[MySQL save_shop_config] 错误: {e}')
        return False

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


# ========== 后台定时同步1688订单 ==========
ORDERS_CACHE_FILE = 'orders_cache.json'

def _sync_orders_task():
    """后台线程：从1688拉订单存到本地缓存"""
    import time as _t
    while True:
        try:
            print(f'[订单同步] 开始从1688同步订单...')
            orders = _1688_fetch_all_shops_orders()
            if orders:
                # 格式化订单为统一格式
                formatted = []
                for o in orders:
                    info = o.get('baseInfo', {})
                    status = info.get('status', '')
                    if status not in ('waitsellersend',):
                        continue
                    item = _1688_format_order(o)
                    item['platform_label'] = '1688'
                    formatted.append(item)
                with open(ORDERS_CACHE_FILE, 'w', encoding='utf-8') as f:
                    json.dump({'orders': formatted, 'updated_at': _t.time()}, f, ensure_ascii=False, default=str)
                print(f'[订单同步] 同步完成: {len(formatted)} 条订单')
            else:
                print(f'[订单同步] 未拉取到订单，缓存不变')
        except Exception as ex:
            print(f'[订单同步] 错误: {ex}')
        _t.sleep(300)  # 5分钟同步一次

# 启动后台同步线程（非守护，确保能写入文件）
import threading as _th
_sync_thread = _th.Thread(target=_sync_orders_task, daemon=True)
_sync_thread.start()
print('[订单同步] 后台同步线程已启动（每5分钟同步一次）')

if __name__ == '__main__':
    print("🏭 飞机盒智能生产管理系统启动中...")
    print("📡 http://0.0.0.0:3001")
    app.run(host='0.0.0.0', port=3002, threaded=True)
