from functools import wraps

import app
from flask import jsonify
import pymysql
from pymysql.cursors import DictCursor

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
        password='Zuoyi980215!',
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