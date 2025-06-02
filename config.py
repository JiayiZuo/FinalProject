# Redis
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_PASSWORD = None
HEALTH_NEWS_CACHE_TTL = 3600  # healthy articles ttl

# Mysql
MYSQL_HOST = '127.0.0.1'
MYSQL_USER= 'root'
MYSQL_PASSWORD = ''
MYSQL_DB = 'medibot'

# MongoDB
MONGODB_CLIENT = "mongodb://localhost:27017/"

# celery
CELERY_BROKER_URL = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

# email
MAIL_SERVER = 'smtp.163.com'
MAIL_PORT = 465
MAIL_USE_SSL = True
MAIL_USE_TLS = False
MAIL_USERNAME = 'medibot@163.com'
MAIL_PASSWORD = 'XFiP4te6JpGgYm4P'
MAIL_DEFAULT_SENDER = 'medibot@163.com'