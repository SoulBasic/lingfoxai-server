import openai
import config
openai.api_key = config.OPENAI_APIKEY
messages = []
system_msg = input("create what?")
messages.append({"role": "system", "content": system_msg})

print("say hello")
while input != "quit()":
    message = input("")
    messages.append({"role": "user", "content": message})
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages)
    reply = response["choices"][0]["message"]["content"]
    messages.append({"role": "assistant", "content": reply})
    print("\n"+reply+"\n")