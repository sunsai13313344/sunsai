from flask import Flask, request, jsonify
import sqlite3
import hashlib
import os

app = Flask(__name__)
DATABASE = "invite.db"

# 初始化数据库
def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    # 邀请码表 code, used, device_hash
    c.execute('''CREATE TABLE IF NOT EXISTS invite_codes
                 (code TEXT PRIMARY KEY, used INTEGER DEFAULT 0, device_hash TEXT)''')
    conn.commit()
    conn.close()

# 获取数据库连接
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# 生成设备指纹简易hash
def get_device_hash(ua, screen):
    raw = ua + "|" + screen
    return hashlib.sha256(raw.encode()).hexdigest()

# 邀请码校验接口
@app.route('/api/verify', methods=['POST'])
def verify():
    data = request.get_json()
    code = data.get('code','').strip()
    ua = data.get('ua','')
    screen = data.get('screen','')
    dev_hash = get_device_hash(ua, screen)

    db = get_db()
    row = db.execute("SELECT * FROM invite_codes WHERE code = ?", (code,)).fetchone()
    if not row:
        return jsonify({"ok":False,"msg":"邀请码不存在"})
    
    if row["used"] == 0:
        # 首次使用，绑定设备
        db.execute("UPDATE invite_codes SET used=1, device_hash=? WHERE code=?",(dev_hash,code))
        db.commit()
        return jsonify({"ok":True,"msg":"验证成功，已绑定当前设备"})
    else:
        # 已被使用，对比设备hash
        if row["device_hash"] == dev_hash:
            return jsonify({"ok":True,"msg":"验证成功，设备匹配"})
        else:
            return jsonify({"ok":False,"msg":"该邀请码已绑定其他设备，无法使用"})

# 查询全部邀请码状态（管理员接口）
@app.route('/api/codes', methods=['GET'])
def get_codes():
    db = get_db()
    rows = db.execute("SELECT * FROM invite_codes").fetchall()
    res = []
    for r in rows:
        res.append({"code":r["code"], "used":r["used"], "device_hash":r["device_hash"]})
    return jsonify(res)

# 初始化内置3个邀请码
@app.before_first_request
def seed_codes():
    db = get_db()
    codes = ["12H4I3","D2OFTX","Y7UEJL"]
    for c in codes:
        db.execute("INSERT OR IGNORE INTO invite_codes(code) VALUES (?)",(c,))
    db.commit()

if __name__ == '__main__':
    init_db()
    app.run(debug=False)
