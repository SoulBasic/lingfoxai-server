import pymysql
import config
import hashlib
import random
import re


class MysqlOperator(object):
    def __init__(self):
        self.conn = pymysql.connect(host=config.DB_HOST, port=3306, user=config.DB_USERNAME, passwd=config.DB_PASSWORD,
                                    db=config.DB_NAME, charset='utf8')
        self.conn.autocommit(False)

    def __del__(self):
        self.conn.close()

    @staticmethod
    def check_format(string: str):
        if re.search(r"\W", string) is None:
            return True
        else:
            return False

    def get_uid_by_username(self, username: str):
        query = "select uid from user where username=%s limit 1"
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, username)
            results = cursor.fetchall()
            if len(results) == 0:
                return -10005, "user not existed", 0
            return 0, "success", int(results[0][0])
        except Exception as err:
            return -10009, err, 0
        finally:
            cursor.close()

    def get_userinfo(self, uid: int):
        query = "select username, usertype, invitation_code, invited_num, balance_num, balance_word from user where uid=%s limit 1"
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, uid)
            results = cursor.fetchall()
            if len(results) == 0:
                return -10004, "user not existed", None
            userinfo = results[0]
            return 0, "success", userinfo
        except Exception as err:
            return -10009, err, None
        finally:
            cursor.close()

    def add_user(self, username: str, password: str):
        query = "INSERT INTO user (username, password, usertype, invitation_code, invited_num, balance_num, balance_word, salt) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        salt = str(random.randint(200000, 800000))
        ivt_code = str(random.randint(200000, 800000))
        hash_pw = hashlib.md5((password + salt).encode('utf-8')).hexdigest()
        param_tuple = (username, hash_pw, 'freetry', ivt_code, 0, 30, 10000, salt)
        try:
            cursor = self.conn.cursor()
            affected_rows = cursor.execute(query, param_tuple)
            if affected_rows == 1:
                self.conn.commit()
                return 0, "success"
            else:
                return -10001, "internal error"
        except Exception as err:
            self.conn.rollback()
            return -10002, err
        finally:
            cursor.close()

    def reset_password(self, uid: int, password: str):
        query = "select salt, password from user where uid=%s limit 1"
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, uid)
            results = cursor.fetchall()
            if len(results) == 0:
                return -10004, "user not existed", None
            salt = results[0][0]
            old_hash_pw = results[0][1]
            hash_pw = hashlib.md5((password + salt).encode('utf-8')).hexdigest()
            if old_hash_pw == hash_pw:
                return -10010, "password same as before"
            query = "update user set password=%s where uid=%s"
            affected_rows = cursor.execute(query, (hash_pw, uid))
            if affected_rows == 1:
                self.conn.commit()
                return 0, "success"
            else:
                return -10001, "internal error"
        except Exception as err:
            self.conn.rollback()
            return -10002, err
        finally:
            cursor.close()

    def check_password(self, username: str, password: str):
        query = "select password, salt from user where username=%s limit 1"
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, username)
            results = cursor.fetchall()
            if len(results) == 0:
                return -10006, "user not existed"
            userinfo = results[0]
            hash_pw = userinfo[0]
            salt = userinfo[1]
            pwhash = hashlib.md5((password + salt).encode("utf-8")).hexdigest()
            if pwhash == hash_pw:
                return 0, "success"
            else:
                return -10007, "password is incorrect"
        except Exception as err:
            return -10002, err
        finally:
            cursor.close()
