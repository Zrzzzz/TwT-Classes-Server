import logging
import os
from datetime import datetime
from logging import handlers

import ddddocr
from flask import Flask, request
from gevent import monkey, pywsgi
from loguru import logger
from loginjs import ctx
from errors import *
import crawler

monkey.patch_all(ssl=False)

class Logger(object):
    level_relations = {
        'debug':logging.DEBUG,
        'info':logging.INFO,
        'warning':logging.WARNING,
        'error':logging.ERROR,
        'crit':logging.CRITICAL
    }#日志级别关系映射

    def __init__(self,filename,level='info',when='D',backCount=3,fmt='%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s'):
        self.logger = logging.getLogger(filename)
        format_str = logging.Formatter(fmt)#设置日志格式
        self.logger.setLevel(self.level_relations.get(level))#设置日志级别

        th = handlers.TimedRotatingFileHandler(filename=filename,when=when,backupCount=backCount,encoding='utf-8')#往文件里写入#指定间隔时间自动生成文件的处理器
        #实例化TimedRotatingFileHandler
        #interval是时间间隔，backupCount是备份文件的个数，如果超过这个个数，就会自动删除，when是间隔的时间单位，单位有以下几种：
        # S 秒
        # M 分
        # H 小时、
        # D 天、
        # W 每星期（interval==0时代表星期一）
        # midnight 每天凌晨
        th.setFormatter(format_str)#设置文件里写入的格式
        self.logger.addHandler(th)


app = Flask(__name__)
ocr = ddddocr.DdddOcr()
if not os.path.exists('logs'):
    os.makedirs('logs')
if not os.path.exists('logs/errors'):
    os.makedirs('logs/errors')
log = Logger('logs/server.log',level='debug')

@app.route('/')
def hello():
    return 'hello'

@app.route('/ocr', methods=["POST"])
def ocrHandler():
    captcha = request.files.get('image')
    if captcha is None:
        return {'code': 202, 'data': '无文件'}
    data = captcha.read()
    try:
        res = ocr.classification(data)
        return {'code': 200, 'data': res}
    except Exception as e:
        with open(f'errors/{datetime.now()}', 'wb') as f:
            f.write(data)
        log.logger.error(e)
        return {'code': 201, 'data': str(e)}

@app.route('/get_classes', methods=["POST"])
def getClasses():
    username = request.form.get('username')
    passwd = request.form.get('passwd')
    try:
        res = crawler.crawl(username, passwd)
        return {'code': 200, 'data': res}
    except Exception as e:
        log.logger.error(e)
        return {'code': 201, 'data': str(e)}

@app.route('/enc', methods=["POST"])
def enc():
    val = request.form.get('val')
    try:
        res = ctx.call('strEnc', val, '1', '2', '3')
        return {'code': 200, 'data': res}
    except Exception as e:
        log.logger.error(e)
        return {'code': 201, 'data': str(e)}


if __name__ == '__main__':
    handler = logging.FileHandler('logs/flask.log', encoding='UTF-8')
    handler.setLevel(logging.WARNING) # 设置日志记录最低级别为DEBUG，低于DEBUG级别的日志记录会被忽略，不设置setLevel()则默认为NOTSET级别。
    logging_format = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(filename)s - %(funcName)s - %(lineno)s - %(message)s')
    handler.setFormatter(logging_format)
    app.logger.addHandler(handler)
    if os.getenv("DEBUG"):
        app.run(host='127.0.0.1', port= 8282, debug=True)
    else:
        try:
            server = pywsgi.WSGIServer(('127.0.0.1', 8282), app)
            server.serve_forever()
        except Exception as e:
            log.logger.error(e)

