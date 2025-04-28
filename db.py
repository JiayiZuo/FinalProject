from functools import wraps

from flask import jsonify
import pymysql
from pymysql.cursors import DictCursor
from pymongo import MongoClient, ASCENDING, DESCENDING

# MySQL 数据库配置
# app.config['MYSQL_HOST'] = 'localhost'
# app.config['MYSQL_USER'] = 'your_username'
# app.config['MYSQL_PASSWORD'] = 'your_password'
# app.config['MYSQL_DB'] = 'your_database'
# app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# 初始化数据库连接
def get_db_connection():
    return pymysql.connect(
        host='127.0.0.1',
        user='root',
        password='{your password}',
        database='medibot',
        cursorclass=DictCursor
    )

def db_query(transaction=False, readonly=False):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            conn = None
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                kwargs['cursor'] = cursor

                result = func(*args, **kwargs)

                # 非只读操作且非事务模式时自动提交
                if not readonly and not transaction:
                    conn.commit()

                return result
            except Exception as e:
                if conn: conn.rollback()
                return jsonify({"error": str(e)}), 500
            finally:
                if conn and not (transaction and not readonly):
                    conn.close()

        return wrapper

    return decorator

# def get_mongo_connection():
#     client = MongoClient("mongodb://localhost:27017/")
#     return client('medibot')
#
# def init_mongo():
#     # 问诊会话集合
#     mongo = get_mongo_connection()
#     consultation_sessions = mongo['consultation_sessions']
#
#     # 创建索引
#     consultation_sessions.create_index([('user_id', ASCENDING)])
#     consultation_sessions.create_index([('start_time', DESCENDING)])
#     consultation_sessions.create_index([('user_id', ASCENDING), ('status', ASCENDING)])

def mongodb_connection(db_name='medibot'):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            client = MongoClient("mongodb://localhost:27017/")
            db = client[db_name]

            try:
                result = func(db, *args, **kwargs)
                return result
            except Exception as e:
                print(f"数据库操作出错: {str(e)}")
                raise
            finally:
                client.close()
        return wrapper
    return decorator
