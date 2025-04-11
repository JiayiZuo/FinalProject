from flask import Flask, jsonify, request
from db import db_query
from datetime import datetime
from utils import validate_user_data
app = Flask(__name__)


@app.route('/userinfo/createuser', methods=['POST'])
@db_query(transaction=False)  # Changed to True for data integrity
def create_user(**kwargs):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

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
                "error": "Validation failed",
                "details": errors
            }), 400

        # Add timestamps
        valid_data['create_time'] = datetime.now()
        valid_data['update_time'] = datetime.now()

        # Build and execute INSERT query more securely
        columns = ', '.join(valid_data.keys())
        placeholders = ', '.join(['%s'] * len(valid_data))
        sql = f"INSERT INTO userinfo ({columns}) VALUES ({placeholders})"
        cursor.execute(sql, list(valid_data.values()))

        cursor.execute("SELECT * FROM userinfo where username = %s", (user_name,))
        new_user = cursor.fetchone()

        return jsonify({
            "status": "success",
            "data": dict(new_user) if new_user else None
        }), 201  # 201 Created for successful resource creation

    except Exception as e:
        # Log the error for debugging
        app.logger.error(f"Error creating user: {str(e)}")
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500

@app.route('/userinfo/updateinfo', methods=['POST'])
@db_query(transaction=False)
def update_userinfo(**kwargs):
    data = request.get_json()
    cursor = kwargs['cursor']
    user_id = data.get('id')

    valid_data, errors = validate_user_data(data)
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400

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
        return jsonify({"error": "user id is required"}), 400
    cursor = kwargs['cursor']
    cursor.execute("SELECT * FROM userinfo WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user)


if __name__ == '__main__':
    app.run()
