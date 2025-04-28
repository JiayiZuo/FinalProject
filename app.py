from flask import Flask, jsonify, request
from db import db_query, mongodb_connection
from pymongo import DESCENDING
from datetime import datetime
from utils import validate_user_data, serialize_document, hash_password_sha256, verify_password_sha256
app = Flask(__name__)


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

if __name__ == '__main__':
    app.run()
