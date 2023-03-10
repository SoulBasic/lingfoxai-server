from Crypto.Cipher import AES
import base64

BLOCK_SIZE = 16  # Bytes
pad = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * \
                chr(BLOCK_SIZE - len(s) % BLOCK_SIZE)
unpad = lambda s: s[:-ord(s[len(s) - 1:])]


def aes_encrypt(key, data):
    key = key.encode('utf8')
    # 字符串补位
    data = pad(data)
    cipher = AES.new(key, AES.MODE_ECB)
    # 加密后得到的是bytes类型的数据，使用Base64进行编码,返回byte字符串
    result = cipher.encrypt(data.encode())
    encodestrs = base64.b64encode(result)
    enctext = encodestrs.decode('utf8')
    return enctext


def aes_decrypt(key, data):
    key = key.encode('utf8')
    data = base64.b64decode(data)
    cipher = AES.new(key, AES.MODE_ECB)
    # 去补位
    text_decrypted = unpad(cipher.decrypt(data))
    text_decrypted = text_decrypted.decode('utf8')
    return text_decrypted
