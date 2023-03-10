import openai
from flask_socketio import SocketIO, emit
import json

def set_api_key(key: str):
    openai.api_key = key


class LingFoxAI(object):
    def __init__(self):
        self.user_conversation = dict()

    def ask(self, question: str, conversation_id: str):
        messages = self.user_conversation.get(conversation_id, list())
        if not messages:
            messages.append({"role": "system", "content": "LingFox AI"})
        messages.append({"role": "user", "content": question})
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages)
        answer = response["choices"][0]["message"]["content"]
        messages.append({"role": "assistant", "content": answer})
        self.user_conversation[conversation_id] = messages
        return answer

    def ask2(self, question: str, conversation_id: str):
        messages = self.user_conversation.get(conversation_id, list())
        if not messages:
            messages.append({"role": "system", "content": "LingFox AI"})
        messages.append({"role": "user", "content": question})
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages)
        except openai.error.OpenAIError as e:
            print(e)
            answer = ""
            return -999, "lingfox ai bot internal error", answer
        except Exception as e:
            print(e)
            answer = ""
            return -999, "server internal error", answer
        answer = response["choices"][0]["message"]["content"]
        messages.append({"role": "assistant", "content": answer})
        self.user_conversation[conversation_id] = messages
        return 0, "success", answer

    def ask_stream(self, question: str, conversation_id: str, rsp_event:str):
        messages = self.user_conversation.get(conversation_id, list())
        if not messages:
            messages.append({"role": "system", "content": "LingFox AI"})
        messages.append({"role": "user", "content": question})
        answer = ""
        try:
            is_start = False
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
                stream=True)
            for part in response:
                finish_reason = part["choices"][0]["finish_reason"]
                if "content" in part["choices"][0]["delta"]:
                    content = part["choices"][0]["delta"]["content"]
                    if not is_start:
                        emit(rsp_event, {'retcode': '0', 'retmsg': 'success', 'cid': conversation_id, 'answer': '', 'is_finish': 'false'})
                        is_start = True
                    emit(rsp_event, {'answer': content, 'is_finish': 'false'})
                    answer += content
                elif finish_reason:
                    pass
            messages.append({"role": "assistant", "content": answer})
            self.user_conversation[conversation_id] = messages
        except openai.error.OpenAIError as e:
            print(e)
            return -999, "lingfox ai bot internal error", answer
        except Exception as e:
            print(e)
            return -999, "server internal error", answer
        print(answer)
        emit(rsp_event, {'answer': '', 'is_finish': 'true'})
        return 0, "success", answer
