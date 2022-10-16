import multiprocessing

bind = "0.0.0.0:8282"

# 启动的进程数
workers = multiprocessing.cpu_count()
worker_class = 'gevent'
