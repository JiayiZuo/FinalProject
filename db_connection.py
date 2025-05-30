from functools import wraps

from flask import jsonify, g
import pymysql
from pymysql.cursors import DictCursor
from pymongo import MongoClient, ASCENDING, DESCENDING, timeout
import redis
from config import *

# init mysql connection
def get_db_connection():
    return pymysql.connect(
        host = MYSQL_HOST,
        user = MYSQL_USER,
        password = MYSQL_PASSWORD,
        database = MYSQL_DB,
        cursorclass = DictCursor
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
            client = MongoClient(MONGODB_CLIENT)
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

# 初始化 Redis 连接
def get_redis():
    if 'redis' not in g:
        g.redis = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
    return g.redis

# Redis 装饰器
def redis_connection(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        redis_conn = get_redis()
        return f(redis_conn, *args, **kwargs)
    return decorated_function
