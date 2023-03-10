import openai


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

    def ask_stream(self, question: str, conversation_id: str):
        messages = self.user_conversation.get(conversation_id, list())
        if not messages:
            messages.append({"role": "system", "content": "LingFox AI"})
        messages.append({"role": "user", "content": question})
        answer = ""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
                stream=True)
            for part in response:
                finish_reason = part["choices"][0]["finish_reason"]
                if "content" in part["choices"][0]["delta"]:
                    content = part["choices"][0]["delta"]["content"]
                    print(content)
                    answer += content
                elif finish_reason:
                    pass
        except openai.error.OpenAIError as e:
            print(e)
            answer = ""
            return -999, "lingfox ai bot internal error", answer
        except Exception as e:
            print(e)
            answer = ""
            return -999, "server internal error", answer
        return 0, "success", answer
