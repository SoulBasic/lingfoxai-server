from flask import Flask, request, render_template
import flask
import logging
import openai
import json
import uuid

app = Flask(__name__,
            static_folder='./www',
            template_folder="./www",
            static_url_path="")
app.logger.setLevel(logging.DEBUG)

openai.api_key = "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"


class LingFoxAI(object):
    def __init__(self):
        self.user_conversation = dict()

    def ask(self, question: str, conversation_id: str):
        messages = self.user_conversation.get(conversation_id, list())
        if not messages:
            messages.append({"role": "system", "content": "LingFox AI"})
        messages.append({"role": "user", "content": question})
        app.logger.info("尝试询问ChatGPT, 问题：" + question)
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages)
        answer = response["choices"][0]["message"]["content"]
        app.logger.info("----------\nChatGPT回答问题：" + question + "\n" + "答案:" + answer + "\n----------")
        messages.append({"role": "assistant", "content": answer})
        self.user_conversation[conversation_id] = messages
        return answer


@app.route('/chat')
def chat():
    rsp = flask.make_response("Bad Request")
    rsp.content_type = "application/json; charset=utf-8"
    rsp.status_code = 200
    rsp.headers["Access-Control-Allow-Origin"] = "*"
    rsp.headers["Access-Control-Expose-Headers"] = "X-Requested-With"
    rsp.headers["Access-Control-Allow-Methods"] = "GET,POST"
    client_ip = request.remote_addr
    question = request.args.get("q", "hello")
    str_uuid = request.args.get("cid", str(uuid.uuid1()))
    app.logger.error("合法请求，来源ip：" + client_ip + ", 问题：" + question)
    answer = ai_bot.ask(question, str_uuid)
    rsp_json = json.dumps({"answer": answer, "cid": str_uuid}, ensure_ascii=False)
    rsp.data = rsp_json
    return rsp


@app.route('/')
def index():
    return render_template('index.html', name='index')


ai_bot = LingFoxAI()

if __name__ == '__main__':
    handler = logging.FileHandler("./log/lingfoxai_server.log", encoding='UTF-8')
    logging_format = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(logging_format)
    app.logger.addHandler(handler)
    app.run(host="0.0.0.0", port=80)
