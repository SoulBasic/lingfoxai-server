import json
import logging
import uuid
import time

import flask
from flask import Flask, request, render_template
from flask_socketio import SocketIO, send

import ai_bot
import config
import db
import encryption
import random

app = Flask(__name__,
            static_folder='../www',
            template_folder="../www",
            static_url_path="")
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)
app.logger.setLevel(logging.DEBUG)

logging_users = dict()


def make_access_token(uid: int, username: str, random_num: int):
    now_time = int(time.time())
    token = dict()
    token["magic"] = "lingfoxai"
    token["uid"] = uid
    token["username"] = username
    token["time"] = now_time
    token["random"] = random_num
    raw_token = json.dumps(token)
    access_token = encryption.aes_encrypt(config.ACCESS_TOKEN_KEY, raw_token)
    return access_token


def parse_access_token(access_token: str):
    if config.DEBUG_MODE == 1:
        token = dict()
        token["uid"] = 1
        token["username"] = "admin"
        return 0, "success", token
    try:
        raw_token = encryption.aes_decrypt(config.ACCESS_TOKEN_KEY, access_token)
        token = json.loads(raw_token)
        uid = token["uid"]
        random_num = logging_users.get(uid, 0)
        if token["magic"] != "lingfoxai" or random_num == 0 or token["random"] != random_num:
            return -106, "bad access token", None
        elif token["time"] - int(time.time()) > config.ACCESS_TOKEN_EXPIRE_TIME:
            return -107, "access token has expired", None

    except Exception as err:
        return -105, "bad access token", None
    return 0, "success", token


@app.route('/chat')
def chat():
    rsp = flask.make_response("")
    rsp.content_type = "application/json; charset=utf-8"
    rsp.status_code = 200
    rsp.headers["Access-Control-Allow-Origin"] = "*"
    rsp.headers["Access-Control-Expose-Headers"] = "X-Requested-With"
    rsp.headers["Access-Control-Allow-Methods"] = "GET,POST"
    client_ip = request.remote_addr
    question = request.args.get("q", "hello")
    str_uuid = request.args.get("cid", str(uuid.uuid1()))
    app.logger.error("合法请求，来源ip：" + client_ip + ", 问题：" + question)
    app.logger.info("尝试询问ChatGPT, 问题：" + question)
    answer = bot.ask(question, str_uuid)
    app.logger.info("----------\nChatGPT回答问题：" + question + "\n" + "答案:" + answer + "\n----------")
    rsp_json = json.dumps({"answer": answer, "cid": str_uuid}, ensure_ascii=False)
    rsp.data = rsp_json
    return rsp


@app.route('/ai/chat', methods=['POST'])
def ai_chat():
    rsp = flask.make_response()
    rsp.content_type = "application/json; charset=utf-8"
    rsp.status_code = 400
    rsp_body = dict()
    access_token = request.cookies.get("access_token", "")
    if access_token == "":
        rsp_body["retcode"] = "-103"
        rsp_body["retmsg"] = "user is not login"
        rsp.data = json.dumps(rsp_body)
        return rsp
    retcode, retmsg, token = parse_access_token(access_token)
    rsp_body["retcode"] = str(retcode)
    rsp_body["retmsg"] = retmsg
    if retcode != 0:
        rsp.data = json.dumps(rsp_body)
        return rsp
    uid = token["uid"]
    rsp.headers["Access-Control-Allow-Origin"] = "*"
    rsp.headers["Access-Control-Expose-Headers"] = "X-Requested-With"
    rsp.headers["Access-Control-Allow-Methods"] = "GET,POST"
    client_ip = request.remote_addr
    str_uuid = str(uuid.uuid1())
    username = ""
    question = "hello"
    try:
        req = json.loads(request.data)
        question = req["question"]
        str_uuid = req["cid"]
    except Exception as err:
        print(err)
    app.logger.error("合法请求，来源ip：" + client_ip + ", 问题：" + question)
    app.logger.info("尝试询问ChatGPT, 问题：" + question)
    retcode, retmsg, answer = bot.ask2(question, str_uuid)
    rsp_body["retcode"] = str(retcode)
    rsp_body["retmsg"] = retmsg
    if retcode != 0:
        rsp.data = json.dumps(rsp_body)
        return rsp
    app.logger.info("----------\nChatGPT回答问题：" + question + "\n" + "答案:" + answer + "\n----------")
    rsp.status_code = 200
    rsp_body["answer"] = answer
    rsp_body["cid"] = str_uuid
    rsp.data = json.dumps(rsp_body, ensure_ascii=False)
    return rsp


@app.route('/user/info', methods=['GET'])
def user_info():
    rsp = flask.make_response()
    rsp.content_type = "application/json; charset=utf-8"
    rsp.status_code = 400
    rsp_body = dict()
    access_token = request.cookies.get("access_token", "")
    if access_token == "":
        rsp_body["retcode"] = "-103"
        rsp_body["retmsg"] = "user is not login"
        rsp.data = json.dumps(rsp_body)
        return rsp
    retcode, retmsg, token = parse_access_token(access_token)
    rsp_body["retcode"] = str(retcode)
    rsp_body["retmsg"] = retmsg
    if retcode != 0:
        rsp.data = json.dumps(rsp_body)
        return rsp
    uid = token["uid"]
    retcode, retmsg, userinfo = dbop.get_userinfo(uid)
    # username, usertype, invitation_code, invited_num, balance_num, balance_word
    rsp.status_code = 200
    rsp_body["username"] = userinfo[0]
    rsp_body["usertype"] = userinfo[1]
    rsp_body["invitation_code"] = userinfo[2]
    rsp_body["invited_num"] = userinfo[3]
    rsp_body["balance_num"] = userinfo[4]
    rsp_body["balance_word"] = userinfo[5]
    rsp.data = json.dumps(rsp_body)
    return rsp


@app.route('/user/logout', methods=['GET'])
def logout():
    rsp = flask.make_response()
    rsp.content_type = "application/json; charset=utf-8"
    rsp.status_code = 400
    rsp_body = dict()
    access_token = request.cookies.get("access_token", "")
    if access_token == "":
        rsp_body["retcode"] = "-103"
        rsp_body["retmsg"] = "user is not login"
        rsp.data = json.dumps(rsp_body)
        return rsp
    retcode, retmsg, token = parse_access_token(access_token)
    rsp_body["retcode"] = str(retcode)
    rsp_body["retmsg"] = retmsg
    if retcode != 0:
        rsp.data = json.dumps(rsp_body)
        return rsp
    uid = token["uid"]
    if 0 != logging_users.get(uid, 0):
        logging_users.pop(uid)
    rsp.status_code = 200
    rsp.data = json.dumps(rsp_body)
    return rsp


@app.route('/user/login', methods=['POST'])
def login():
    rsp = flask.make_response()
    rsp.content_type = "application/json; charset=utf-8"
    rsp.status_code = 400
    rsp_body = dict()
    try:
        req = json.loads(request.data)
        username = req["username"]
        password = req["password"]
        if False == dbop.check_format(username) or False == dbop.check_format(password):
            rsp_body["retcode"] = "-100"
            rsp_body["retmsg"] = "username or password has illegal characters"
            rsp.data = json.dumps(rsp_body)
            return rsp
        retcode, retmsg = dbop.check_password(username, password)
        rsp_body["retcode"] = str(retcode)
        rsp_body["retmsg"] = retmsg
        if retcode != 0:
            rsp.data = json.dumps(rsp_body)
            return rsp
        retcode, retmsg, uid = dbop.get_uid_by_username(username)
        rsp_body["retcode"] = str(retcode)
        rsp_body["retmsg"] = retmsg
        if retcode != 0:
            rsp.data = json.dumps(rsp_body)
            return rsp
        retcode, retmsg, userinfo = dbop.get_userinfo(uid)
        rsp_body["retcode"] = str(retcode)
        rsp_body["retmsg"] = retmsg
        if retcode != 0:
            rsp.data = json.dumps(rsp_body)
            return rsp
        # usertype, invitation_code, invited_num, balance_num, balance_word
        rsp.status_code = 200
        random_num = random.randint(200000, 800000)
        if 0 != logging_users.get(uid, 0):
            logging_users.pop(uid)
        logging_users[uid] = random_num
        access_token = make_access_token(uid, username, random_num)
        rsp.set_cookie("access_token", access_token)
        rsp_body["username"] = userinfo[0]
        rsp_body["usertype"] = userinfo[1]
        rsp_body["invitation_code"] = userinfo[2]
        rsp_body["invited_num"] = userinfo[3]
        rsp_body["balance_num"] = userinfo[4]
        rsp_body["balance_word"] = userinfo[5]
        rsp.data = json.dumps(rsp_body)
    except Exception as err:
        print(err)
        rsp.status_code = 400
        rsp_body["retcode"] = "-100"
        rsp_body["retmsg"] = "bad request"
        rsp.data = json.dumps(rsp_body)
    return rsp


@app.route('/user/register', methods=['POST'])
def register():
    rsp = flask.make_response()
    rsp.content_type = "application/json; charset=utf-8"
    rsp.status_code = 400
    rsp_body = dict()
    try:
        req = json.loads(request.data)
        username = req["username"]
        password = req["password"]
        if False == dbop.check_format(username) or False == dbop.check_format(password):
            rsp_body["retcode"] = "-100"
            rsp_body["retmsg"] = "username or password has illegal characters"
            rsp.data = json.dumps(rsp_body)
            return rsp
        retcode, retmsg, uid = dbop.get_uid_by_username(username)
        if uid != 0:
            rsp_body["retcode"] = "-111"
            rsp_body["retmsg"] = "user existed"
            rsp.data = json.dumps(rsp_body)
            return rsp
        retcode, retmsg = dbop.add_user(username, password)
        rsp_body["retcode"] = str(retcode)
        rsp_body["retmsg"] = retmsg
        if retcode == 0:
            rsp.status_code = 200
        rsp.data = json.dumps(rsp_body)
        return rsp
    except Exception as err:
        print(err)
        rsp.status_code = 400
        rsp_body["retcode"] = "-100"
        rsp_body["retmsg"] = "bad request"
        rsp.data = json.dumps(rsp_body)
    return rsp


@app.route('/')
def index():
    return render_template('index.html', name='index')


chat_stream_namespace = '/stream'


@socketio.on('connect', namespace=chat_stream_namespace)
def connected_msg():
    print('client connected.')


@socketio.on('disconnect', namespace=chat_stream_namespace)
def disconnect_msg():
    print('client disconnected.')


@socketio.on('json', namespace=chat_stream_namespace)
def handle_json(question):
    print('received json: ' + str(question))
    send(question, json=True)


ai_bot.set_api_key(config.OPENAI_APIKEY)
bot = ai_bot.LingFoxAI()
dbop = db.MysqlOperator()

if __name__ == '__main__':
    socketio.init_app(app, cors_allowed_origins='*')
    handler = logging.FileHandler("../log/lingfoxai_server.log", encoding='UTF-8')
    logging_format = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(logging_format)
    app.logger.addHandler(handler)
    socketio.run(app, host='0.0.0.0', port=80)
