import json
import logging
import uuid
import time
import flask
from flask import Flask, request, render_template
from flask_socketio import SocketIO, emit

import ai_bot
import config
import db
import encryption
import random

app = Flask(__name__,
            static_folder=config.SERVER_STATIC_FOLDER,
            template_folder=config.SERVER_TEMPLATE_FOLDER,
            static_url_path="")
app.config['SECRET_KEY'] = config.SERVER_SECRET_KEY
socketio = SocketIO(app, async_mode=None)
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
    if access_token == config.ADMIN_DEBUG_ACCESS_TOKEN:
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


@app.route('/ai/create', methods=['POST'])
def ai_create():
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
    rsp.headers["Access-Control-Allow-Origin"] = "*"
    rsp.headers["Access-Control-Expose-Headers"] = "X-Requested-With"
    rsp.headers["Access-Control-Allow-Methods"] = "GET,POST"
    client_ip = request.remote_addr
    str_uuid = str(uuid.uuid1())
    language = str()
    title = str()
    element = str()
    try:
        req = json.loads(request.data)
        language = req["language"]
        title = req["title"]
        element = req["element"]
    except Exception as err:
        print(err)
        rsp.status_code = 400
        rsp_body["retcode"] = "-100"
        rsp_body["retmsg"] = "bad request"
        rsp.data = json.dumps(rsp_body)
        return rsp
    try:
        str_uuid = req["cid"]
    except Exception as err:
        print(err)
    question = "请你帮我用\"" + language + "\"，写3段\"" + title + "\"，需要包含以下要素信息：\"" + element + "\",字数限定为1000字以上"
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


@app.route('/ai/translate', methods=['POST'])
def ai_translate():
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
    rsp.headers["Access-Control-Allow-Origin"] = "*"
    rsp.headers["Access-Control-Expose-Headers"] = "X-Requested-With"
    rsp.headers["Access-Control-Allow-Methods"] = "GET,POST"
    client_ip = request.remote_addr
    str_uuid = str(uuid.uuid1())
    try:
        req = json.loads(request.data)
        language = req["language"]
        content = req["content"]
    except Exception as err:
        print(err)
        rsp.status_code = 400
        rsp_body["retcode"] = "-100"
        rsp_body["retmsg"] = "bad request"
        rsp.data = json.dumps(rsp_body)
        return rsp
    try:
        str_uuid = req["cid"]
    except Exception as err:
        print(err)
    question = "请你帮我把\"" + content + "\"翻译成\"" + language + "\"，直接输出结果不要加引号"
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


@app.route('/ai/rewrite', methods=['POST'])
def ai_rewrite():
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
    rsp.headers["Access-Control-Allow-Origin"] = "*"
    rsp.headers["Access-Control-Expose-Headers"] = "X-Requested-With"
    rsp.headers["Access-Control-Allow-Methods"] = "GET,POST"
    client_ip = request.remote_addr
    str_uuid = str(uuid.uuid1())
    try:
        req = json.loads(request.data)
        content = req["content"]
        style = req["style"]
    except Exception as err:
        print(err)
        rsp.status_code = 400
        rsp_body["retcode"] = "-100"
        rsp_body["retmsg"] = "bad request"
        rsp.data = json.dumps(rsp_body)
        return rsp
    try:
        str_uuid = req["cid"]
    except Exception as err:
        print(err)
    question = "请你帮我把下边这段话，使用\"" + style + "\"的风格进行优化一下，优化前后语种请保持不变。原话为：\"" + content + "\""
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


@app.route('/user/resetpassword', methods=['POST'])
def reset_password():
    rsp = flask.make_response()
    rsp.content_type = "application/json; charset=utf-8"
    rsp.status_code = 400
    rsp_body = dict()
    try:
        req = json.loads(request.data)
        username = req["username"]
        password = req["password"]
        new_password = req["new_password"]
        if False == dbop.check_format(new_password):
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
        retcode, retmsg = dbop.reset_password(uid, new_password)
        rsp_body["retcode"] = str(retcode)
        rsp_body["retmsg"] = retmsg
        if retcode == 0:
            rsp.status_code = 200
        rsp.data = json.dumps(rsp_body)
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


stream_namespace = "/stream"


@socketio.on('connect', namespace=stream_namespace)
def on_connect():
    print('Client connected', request.sid)


@socketio.on('disconnect', namespace=stream_namespace)
def on_disconnect():
    print('Client disconnected', request.sid)


@socketio.event(namespace=stream_namespace)
def ai_chat(message):
    rsp_event = "ai_chat_response"
    str_uuid = str(uuid.uuid1())
    try:
        question = message["question"]
        print(question)
        access_token = message["access_token"]
    except Exception as err:
        print(err)
        retcode = "-100"
        retmsg = "bad request"
        emit(rsp_event, {'retcode': str(retcode), 'retmsg': retmsg, 'answer': '', 'is_finish': 'false'})
        return
    try:
        str_uuid = message["cid"]
    except Exception as err:
        print(err)
    retcode, retmsg, token = parse_access_token(access_token)
    if retcode != 0:
        emit(rsp_event, {'retcode': str(retcode), 'retmsg': retmsg, 'answer': '', 'is_finish': 'true'})
    else:
        client_ip = request.remote_addr
        app.logger.error("合法请求，来源ip：" + client_ip + ", 问题：" + question)
        app.logger.info("尝试询问ChatGPT(stream), 问题：" + question)
        retcode, retmsg, answer = bot.ask_stream(question, str_uuid, rsp_event)
        app.logger.info("----------\nChatGPT回答问题：" + question + "\n" + "答案:" + answer + "\n----------")


@socketio.event(namespace=stream_namespace)
def ai_translate(message):
    rsp_event = "ai_translate_response"
    str_uuid = str(uuid.uuid1())
    try:
        language = message["language"]
        content = message["content"]
        access_token = message["access_token"]
    except Exception as err:
        print(err)
        retcode = "-100"
        retmsg = "bad request"
        emit(rsp_event, {'retcode': str(retcode), 'retmsg': retmsg, 'answer': '', 'is_finish': 'false'})
        return
    try:
        str_uuid = message["cid"]
    except Exception as err:
        print(err)
    retcode, retmsg, token = parse_access_token(access_token)
    if retcode != 0:
        emit(rsp_event, {'retcode': str(retcode), 'retmsg': retmsg, 'answer': '', 'is_finish': 'true'})
    else:
        client_ip = request.remote_addr
        question = "请你帮我把\"" + content + "\"翻译成\"" + language + "\"，直接输出结果不要加引号"
        app.logger.error("合法请求，来源ip：" + client_ip + ", 问题：" + question)
        app.logger.info("尝试询问ChatGPT(stream), 问题：" + question)
        retcode, retmsg, answer = bot.ask_stream(question, str_uuid, rsp_event)
        app.logger.info("----------\nChatGPT回答问题：" + question + "\n" + "答案:" + answer + "\n----------")


@socketio.event(namespace=stream_namespace)
def ai_rewrite(message):
    rsp_event = "ai_rewrite_response"
    str_uuid = str(uuid.uuid1())
    try:
        language = message["language"]
        content = message["content"]
        style = message["style"]
        access_token = message["access_token"]
    except Exception as err:
        print(err)
        retcode = "-100"
        retmsg = "bad request"
        emit(rsp_event, {'retcode': str(retcode), 'retmsg': retmsg, 'answer': '', 'is_finish': 'false'})
        return
    try:
        str_uuid = message["cid"]
    except Exception as err:
        print(err)
    retcode, retmsg, token = parse_access_token(access_token)
    if retcode != 0:
        emit(rsp_event, {'retcode': str(retcode), 'retmsg': retmsg, 'answer': '', 'is_finish': 'true'})
    else:
        client_ip = request.remote_addr
        question = "请你帮我把下边这段话，使用\"" + style + "\"的风格进行优化一下，优化前后语种请保持不变。原话为：\"" + content + "\""
        app.logger.error("合法请求，来源ip：" + client_ip + ", 问题：" + question)
        app.logger.info("尝试询问ChatGPT(stream), 问题：" + question)
        retcode, retmsg, answer = bot.ask_stream(question, str_uuid, rsp_event)
        app.logger.info("----------\nChatGPT回答问题：" + question + "\n" + "答案:" + answer + "\n----------")


ai_bot.set_api_key(config.OPENAI_APIKEY)
bot = ai_bot.LingFoxAI()
dbop = db.MysqlOperator()

if __name__ == '__main__':
    handler = logging.FileHandler(config.SERVER_LOG_PATH, encoding='UTF-8')
    logging_format = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(logging_format)
    app.logger.addHandler(handler)
    socketio.run(app, host='0.0.0.0', port=config.SERVER_PORT, allow_unsafe_werkzeug=True)
