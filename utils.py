import hashlib

def hash_password_sha256(password):
    # 使用 SHA-256 哈希算法
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password_sha256(stored_password_hash, password):
    return stored_password_hash == hash_password_sha256(password)

def validate_user_data(update_data):
    errors = {}
    valid_data = {}

    if 'username' in update_data:
        if not 2 <= len(update_data['username']) <= 20:
            errors['username'] = "Length must be 2-20 characters"
        else:
            valid_data['username'] = update_data['username'].strip()
    if 'age' in update_data:
        try:
            age = int(update_data['age'])
            if not 0 <= age <= 120:
                errors['age'] = "Must be 0-120"
            else:
                valid_data['age'] = age
        except ValueError:
            errors['age'] = "Must be integer"
    if 'height' in update_data:
        try:
            if not 0 <= update_data['height'] <= 300:
                errors['height'] = "Must be 0-300"
            else:
                valid_data['height'] = update_data['height']
        except ValueError:
            errors['height'] = "Must be decimal"
    if 'weight' in update_data:
        try:
            if not 0 <= update_data['weight'] <= 1000:
                errors['weight'] = "Must be 0-1000"
            else:
                valid_data['weight'] = update_data['weight']
        except ValueError:
            errors['weight'] = "Must be decimal"
    return valid_data, errors


def serialize_document(document):
    document['_id'] = str(document['_id'])
    return document