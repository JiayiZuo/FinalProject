from flask import Flask, jsonify, request
from db_connection import db_query, mongodb_connection, redis_connection
from pymongo import DESCENDING
from datetime import datetime
from utils import validate_user_data, serialize_document, hash_password_sha256, verify_password_sha256
from constant import *
from config import *
import requests, json, re
from celery import Celery
from flask_mail import Mail
app = Flask(__name__)

app.config['MAIL_SERVER'] = MAIL_SERVER
app.config['MAIL_PORT'] = MAIL_PORT
app.config['MAIL_USE_SSL'] = MAIL_USE_SSL
app.config['MAIL_USE_TLS'] = MAIL_USE_TLS
app.config['MAIL_USERNAME'] = MAIL_USERNAME
app.config['MAIL_PASSWORD'] = MAIL_PASSWORD
app.config['MAIL_DEFAULT_SENDER'] = MAIL_DEFAULT_SENDER
mail = Mail(app)

@app.route('/userinfo/createuser', methods=['POST'])
@db_query(transaction=False)  # Changed to True for data integrity
def create_user(**kwargs):
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error",
                "data": {},
                "message": "No data provided"
            }), 400

        cursor = kwargs['cursor']
        user_name = data.get('username')

        # Check if username exists (more secure parameterized query)
        cursor.execute("SELECT * FROM userinfo WHERE username = %s", (user_name,))
        if cursor.fetchone():
            return jsonify({"data": "Username already exists"}), 409

        # Validate user data
        valid_data, errors = validate_user_data(data)
        if errors:
            return jsonify({
                "status": "error",
                "data": {},
                "message": "Invalid user data"
            }), 400

        # Add timestamps
        valid_data['create_time'] = datetime.now()
        valid_data['update_time'] = datetime.now()
        valid_data['password_hash'] = hash_password_sha256(data.get('password'))

        # Build and execute INSERT query more securely
        columns = ', '.join(valid_data.keys())
        placeholders = ', '.join(['%s'] * len(valid_data))
        sql = f"INSERT INTO userinfo ({columns}) VALUES ({placeholders})"
        cursor.execute(sql, list(valid_data.values()))

        cursor.execute("SELECT * FROM userinfo where username = %s", (user_name,))
        new_user = cursor.fetchone()
        new_user = dict(new_user)
        del new_user['password_hash']

        return jsonify({
            "status": "success",
            "data": new_user
        })

    except Exception as e:
        app.logger.error(f"Error creating user: {str(e)}")
        return jsonify({
            "status": "error",
            "data": {},
            "messages": str(e),
        })

@app.route('/userinfo/updateinfo', methods=['POST'])
@db_query(transaction=False)
def update_userinfo(**kwargs):
    data = request.get_json()
    cursor = kwargs['cursor']
    user_id = data.get('id')

    valid_data, errors = validate_user_data(data)
    if errors:
        return jsonify({
            "status": "error",
            "data": {},
            "message": errors
        }), 400

    valid_data['update_time'] = datetime.now()
    set_clause = ", ".join([f"{k} = %s" for k in valid_data.keys()])
    sql = f"""UPDATE userinfo SET {set_clause} WHERE id = %s"""


    cursor.execute(sql, (*valid_data.values(), user_id))

    cursor.execute("SELECT * FROM userinfo WHERE id = %s", (user_id,))
    user = cursor.fetchone()

    return jsonify({
        "status": "success",
        "data": user
    })

@app.route('/userinfo/getinfo', methods=['GET'])
@db_query(transaction=False, readonly=True)
def get_userinfo(**kwargs):
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({
            "status": "error",
            "data": {},
            "message": "user id is required"
        }), 400
    cursor = kwargs['cursor']
    cursor.execute("SELECT * FROM userinfo WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    if not user:
        return jsonify({
            "status": "error",
            "data": {},
            "message": "User not found"
        }), 404
    return jsonify({
        "status": "success",
        "data": user
    })

@app.route('/user/login', methods=['POST'])
@db_query(transaction=False, readonly=True)
def user_login(**kwargs):
    data = request.get_json()
    username = data['username']
    password = data['password']
    if not username:
        return jsonify({
            "status": "error",
            "data": {},
            "message": "username and password are required"
        }), 400
    cursor = kwargs['cursor']
    cursor.execute("SELECT * FROM userinfo WHERE username = %s", (username,))
    user = cursor.fetchone()
    if not user:
        return jsonify({
            "status": "error",
            "data": {},
            "message": "User not found"
        }), 404
    if not verify_password_sha256(user['password_hash'], password):
        return jsonify({
            "status": "error",
            "data": {},
            "message": "Invalid user password"
        }), 401
    del user['password_hash']
    return jsonify({
        "status": "success",
        "data": user
    })

@app.route('/consultation/create', methods=['POST'])
@mongodb_connection()
def create_consultation(mongo):
    data = request.get_json()
    # todo username和id对应关系校验
    if not data or 'user_id' not in data or 'username' not in data:
        return jsonify({"data": "No data provided"}), 400
    session_data = {
        'user_id': data.get('user_id'),
        'username': data.get('username'),
        'start_time': datetime.now(),
        'messages': data.get('messages'), # [{},{}]
        'updated_at': datetime.now()
    }
    try:
        result = mongo.consultation_sessions.insert_one(session_data)
        data['session_id'] = str(result.inserted_id)
        return jsonify({
            "status": "success",
            "data": data,
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'message': 'Failed to create consultation session'
        }), 500

@app.route('/consultation/get', methods=['GET'])
@mongodb_connection()
def get_consultation(mongo):
    user_id = request.args.get('user_id')
    is_all = int(request.args.get('is_all')) # 1-get all documents 0-get recently documents
    sessions = mongo.consultation_sessions.find({'user_id': int(user_id)}).sort('start_time', DESCENDING)
    data = {
        'user_id': user_id,
        'messages': []
    }
    if not is_all:
        try:
            session = sessions[0]
        except IndexError:
            return jsonify({
                'status': 'success',
                'data': data
            })
        session = serialize_document(session)
        data['messages'].append(session)
        return jsonify({
            'status': 'success',
            'data': data
        })
    for session in sessions:
        session = serialize_document(session)
        data['messages'].append(session)
    return jsonify({
        "status": "success",
        "data": data
    })

@app.route('/info/articles', methods=['GET'])
@redis_connection
def get_healthy_articles(redis):
    keyword = request.args.get('keyword', '')
    if keyword == '':
        articles_cache = redis.get('healthy_articles')
        if articles_cache is not None:
            articles_cache = json.loads(articles_cache)
            return jsonify({
                'status': 'success',
                'data': {
                    'articles': articles_cache,
                    'count': len(articles_cache)
                },
                'messages': 'Get health articles successful'
            })

    params = {
        'keyword': keyword,
    }

    try:
        response = requests.get(HEALTHY_MESSAGE_URL, params=params)
        response.raise_for_status()
        data = response.json()

        if data['Result']['Error'] != 'False':
            return jsonify({
                'status': 'error',
                'data': {},
                'messages': 'Get health articles failed'
            }), 200

        resources = data['Result']['Resources']['Resource']
        articles = []
        for resource in resources:
            article_info = {
                'category': resource['Categories'],
                'title': resource['Title'],
                'picture': resource['ImageUrl'],
                'url': resource['AccessibleVersion'],
            }
            articles.append(article_info)
        if keyword == '':
            redis.set('healthy_articles', json.dumps(articles), ex=HEALTH_NEWS_CACHE_TTL)

        return jsonify({
            'status': 'success',
            'data': {
                'articles': articles,
                'count': len(articles)
            },
            'messages': 'Get health articles successful'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
@app.route('/reminder/create', methods=['POST'])
@db_query(transaction=False)
def medicine_reminder_create(**kwargs):
    data = request.json
    required_fields = ['user_id', 'medicine_name', 'reminder_times', 'email']

    if not all(field in data for field in required_fields):
        return jsonify({
            'status': 'error',
            'data': {},
            'message': 'missing required fields'
        })

    times = data['reminder_times'].split(',')
    try:
        for t in times:
            # time format (HH:MM)
            time_str = t.strip()
            if len(time_str) != 5 or time_str[2] != ':':
                raise ValueError
            hour = int(time_str[:2])
            minute = int(time_str[3:])
            if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                raise ValueError
    except ValueError:
        return jsonify({
            'status': 'error',
            'data': {},
            'message': 'invalid time format，using HH:MM format（example 08:00）'
        })

    if not re.match(r"[^@]+@[^@]+\.[^@]+", data['email']):
        return jsonify({
            'status': 'error',
            'data': {},
            'message': 'invalid email format'
        })

    cursor = kwargs['cursor']
    insert_data = {
        'user_id': data['user_id'],
        'medicine_name': data['medicine_name'],
        'reminder_times': data['reminder_times'],
        'start_date': data.get('start_date', datetime.now()),
        'end_date': data.get('end_date', datetime.now()),
        'email': data['email'],
        'is_active': 1
    }
    placeholders = ', '.join(['%s'] * len(insert_data))
    columns = ', '.join(insert_data.keys())
    sql = f"INSERT INTO medication_reminder ({columns}) VALUES ({placeholders})"

    cursor.execute(sql, list(insert_data.values()))
    reminder_times = data['reminder_times'].split(',')

    return jsonify({
        'status': 'success',
        'data': {
            'user_id': data['user_id'],
            'reminder_times': reminder_times,
        },
        'message': 'create reminder successful'
    })

@app.route('/reminder/get', methods=['GET'])
@db_query(transaction=False)
def medicine_reminder_get(**kwargs):
    cursor = kwargs['cursor']
    user_id = request.args.get('user_id', '')
    reminder_id = request.args.get('reminder_id', '')
    if not user_id and not reminder_id:
        return jsonify({
            'status': 'error',
            'data': {},
            'message': 'user_id or reminder_id need to be provided'
        })
    if user_id and reminder_id:
        cursor.execute("SELECT * FROM medication_reminder WHERE user_id = %s and id = %s", (user_id, reminder_id))
        reminder = cursor.fetchall()
        return jsonify({
            'status': 'success',
            'data': {
                'reminder': reminder,
                'count': len(reminder)
            },
            'message': 'reminder found by current user'
        })

    if user_id:
        cursor.execute("SELECT * FROM medication_reminder WHERE user_id = %s", (user_id,))
        reminder = cursor.fetchall()
        return jsonify({
            'status': 'success',
            'data': {
                'reminder': reminder,
                'count': len(reminder)
            },
            'message': 'reminder found by current user'
        })

    if reminder_id:
        cursor.execute("SELECT * FROM medication_reminder WHERE id = %s", (reminder_id,))
        reminder = cursor.fetchone()
        return jsonify({
            'status': 'success',
            'data': {
                'reminder': reminder,
                'count': 1
            },
            'message': 'reminder found by reminder_id'
        })

@app.route('/reminder/update', methods=['POST'])
@db_query(transaction=False)
def medicine_reminder_update(**kwargs):
    data = request.json
    cursor = kwargs['cursor']
    reminder_id = data['reminder_id']

    cursor.execute("SELECT * FROM medication_reminder WHERE id = %s", (reminder_id,))
    reminder = cursor.fetchone()

    if not reminder:
        return jsonify({
            'status': 'error',
            'data': {},
            'message': 'reminder not found'
        })

    if 'reminder_times' in data:
        times = data['reminder_times'].split(',')
        try:
            for t in times:
                time_str = t.strip()
                if len(time_str) != 5 or time_str[2] != ':':
                    raise ValueError
                hour = int(time_str[:2])
                minute = int(time_str[3:])
                if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                    raise ValueError
        except ValueError:
            return jsonify({
                'status': 'error',
                'data': {},
                'message': 'invalid time format，using HH:MM format（example 08:00）'
            })

    if 'email' in data:
        if not re.match(r"[^@]+@[^@]+\.[^@]+", data['email']):
            return jsonify({
                'status': 'error',
                'data': {},
                'message': 'invalid email format'
            })

    update_fields = []
    update_values = []

    updatable_fields = [
        'medicine_name', 'reminder_times', 'dosage', 'frequency',
        'start_date', 'end_date', 'is_active', 'email'
    ]

    for field in updatable_fields:
        if field in data:
            update_fields.append(f"{field} = %s")
            update_values.append(data[field])

    try:
        update_fields.append("updated_at = %s")
        update_values.append(datetime.now())

        update_values.append(reminder_id)

        set_clause = ", ".join(update_fields)
        sql = f"UPDATE medication_reminder SET {set_clause} WHERE id = %s"

        cursor.execute(sql, update_values)

        cursor.execute("SELECT * FROM medication_reminder WHERE id = %s", (reminder_id,))
        updated_reminder = cursor.fetchone()

        return jsonify({
            'status': 'success',
            'data': {
                'id': updated_reminder['id'],
                'medicine_name': updated_reminder['medicine_name'],
                'reminder_times': updated_reminder['reminder_times'].split(','),
                'email': updated_reminder['email'],
                'is_active': bool(updated_reminder['is_active'])
            },
            'message': 'reminder updated successfully'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'data': {},
            'message': e
        })

@app.route('/reminder/delete', methods=['POST'])
@db_query(transaction=True)
def medicine_reminder_delete(**kwargs):
    cursor = kwargs['cursor']
    reminder_id = request.json['reminder_id']

    cursor.execute("SELECT * FROM medication_reminder WHERE id = %s", (reminder_id,))
    reminder = cursor.fetchone()

    if not reminder:
        return jsonify({
            'status': 'error',
            'data': {},
            'message': 'reminder not found'
        })

    try:
        cursor.execute("DELETE FROM medication_reminder WHERE id = %s", (reminder_id,))

        return jsonify({
            'status': 'success',
            'data': {
                'deleted_id': reminder_id
            },
            'message': 'reminder deleted successfully'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'data': {},
            'message': e
        })


if __name__ == '__main__':
    app.run()
