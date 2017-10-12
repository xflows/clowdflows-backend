import multiprocessing

bind = "unix:/tmp/gunicorn.sock"
workers = multiprocessing.cpu_count() * 2 + 1
timeout = 300
errorlog = '/var/log/cfapi-gunicorn.error.log'
loglevel = 'info'
