from flask import session, make_response, Flask, request, render_template,redirect,jsonify
#数据库交互
import pymysql
import time,datetime
import random,string
from geetest import GeetestLib
import json
import os
import threading


geetest_id = "4a58e5052ce"
geetest_key = "76ebebb658"

os.system("")
app = Flask(__name__)
app.secret_key = 'i-like-shorturl'

###功能
def short_url(url,name,type):
    try:
        db = pymysql.connect("localhost","root","root","url" )
        cursor = db.cursor()
        sql = "SELECT url FROM data where name = %s"
        try:
            cursor.execute(sql,[name])
            results = cursor.fetchone()
            if not results:
                start = datetime.datetime.now()
                unixtime = time.mktime(time.strptime(start.strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S'))
                sql = "INSERT INTO data(url, name, time, type) VALUES (%s, %s, %s, %s)"
                cursor.execute(sql,[url,name,unixtime,type])
                db.commit()
                return '成功'
            else:
                return '后缀已存在，请重试'
        except:
            db.rollback()
            return '缩短网址操作失败'
        cursor.close()
        db.close()
    except:
        return '连接数据库操作失败'

#检查非法字符
def filter(url,name,type):
    if 'https://' in url:
        passid = 1
    elif 'http://' in url:
        passid = 1
    else:
        passid = 0
    if passid == 1:
        if len(url) <= 250:
            if name.isalnum() and len(name) <= 250:
                if type in ['1','2','3','4','5']:
                    return '通过检查'
                else:
                    return '超出范围，非法操作'
            else:
                return '后缀只能由字母数字组合，最大长度250'
        else:
            return '网址最大长度250'
    else:
        return '请带上 http(s):// '

#定时删除
def del_url():
    try:
        db = pymysql.connect("localhost","root","root","url" )
        cursor = db.cursor()
        while True:
            #重新排序
            sql_reid1 = 'ALTER TABLE data DROP id'
            sql_reid2 = 'ALTER TABLE data ADD id MEDIUMINT(8) NOT NULL FIRST'
            sql_reid3 = 'ALTER TABLE data MODIFY COLUMN id int(8) NOT NULL AUTO_INCREMENT,ADD PRIMARY KEY(id)'
            try:
                cursor.execute(sql_reid1)
                db.commit()
            except:
                pass
            cursor.execute(sql_reid2)
            cursor.execute(sql_reid3)
            db.commit()
            #查询数量
            sql_count = "SELECT count(*) FROM data"
            cursor.execute(sql_count)
            count = cursor.fetchone()
            for id in range(1,count[0]+1):
                sql_time = "SELECT time,type FROM data WHERE id = %s"
                cursor.execute(sql_time,[id])
                data = cursor.fetchone()
                unixtime = data[0]
                type = data[1]
                #计算时间间隔
                timed = datetime.datetime.fromtimestamp(float(unixtime))
                now_time = datetime.datetime.now()
                interval_s = (now_time - timed).total_seconds()
                interval_h = interval_s//3600
                #判断有效时间类型
                if type == '1':
                    if interval_h >= 1:
                        sql_del = "DELETE FROM data WHERE id = %s"
                        cursor.execute(sql_del,[id])
                        db.commit()
                elif type == '2':
                    if interval_h >= 24:
                        sql_del = "DELETE FROM data WHERE id = %s"
                        cursor.execute(sql_del,[id])
                        db.commit()
                elif type == '3':
                    if interval_h >= 168:
                        sql_del = "DELETE FROM data WHERE id = %s"
                        cursor.execute(sql_del,[id])
                        db.commit()
                elif type == '4':
                    if interval_h >= 720:
                        sql_del = "DELETE FROM data WHERE id = %s"
                        cursor.execute(sql_del,[id])
                        db.commit()
                elif type == '5':
                    if interval_h >= 8760:
                        sql_del = "DELETE FROM data WHERE id = %s"
                        cursor.execute(sql_del,[id])
                        db.commit()
            time.sleep(60)
    except:
        print(' * 链接有效期功能失效,重试')




#视图层
#跳转功能
@app.route('/<name>')
def redirecturl(name):
    try:
        db = pymysql.connect("localhost","root","root","url" )
        cursor = db.cursor()
        sql = "SELECT url FROM data where name = %s"
        try:
            cursor.execute(sql,[name])
            results = cursor.fetchall()
            url = results[0][0]
        except:
            db.rollback()
        db.close()
        return redirect('%s'%(url),code=301)
    except:
        return 'Error'


#缩短域名功能
@app.route('/',methods=['GET','POST'])
def index():
    global updata_time,all_count,valid_count,spider_status_list
    if request.method == 'POST':
        gt = GeetestLib(geetest_id, geetest_key)
        challenge = request.form[gt.FN_CHALLENGE]
        validate = request.form[gt.FN_VALIDATE]
        seccode = request.form[gt.FN_SECCODE]
        status = session[gt.GT_STATUS_SESSION_KEY]
        user_id = session["user_id"]
        #获取数据
        url = request.values.get('url')
        name = request.values.get('name')
        type = request.values.get('type')
        if status:
            result = gt.success_validate(challenge, validate, seccode, user_id)
        else:
            result = gt.failback_validate(challenge, validate, seccode)
        if result:
            #成功验证
            if not name:
                #生成随机6位
                pool = string.ascii_letters+string.digits
                key=[]
                key=random.sample(pool,6)
                keys="".join(key)
                name = keys
            check = filter(url,name,type)
            if '通过检查' in check:
                info = short_url(url,name,type)
                if '成功' in info:
                    return jsonify({"code": 200, "info": name})
                else:
                    return jsonify({"code": 403, "info": info})
            else:
                return jsonify({"code": 403, "info": check})
        else:
            return jsonify({"code": 403, "info": "滑动验证未通过"})

    else:
        return render_template('index.html')


#以下为滑动验证
@app.route('/captcha', methods=["GET"])
def get_captcha():
    user_id = 'shorturl'
    gt = GeetestLib(geetest_id, geetest_key)
    status = gt.pre_process(user_id)
    session[gt.GT_STATUS_SESSION_KEY] = status
    session["user_id"] = user_id
    response_str = gt.get_response_str()
    return response_str

del_task = threading.Thread(target=del_url,args=())
del_task.start()

if __name__ == '__main__':

    #不能开debug，否则子线程会被运行两次
    app.run()
