
import logging
import os, sys

from conf.config import log_level

logger = logging.getLogger('my_logger')
logger.setLevel(log_level)

date_str = str(datetime.datetime.now().today().date())
log_folder = BASE_DIR + '/data/logs/' + date_str.split('-')[0] + '/' + date_str.split('-')[1] + '/'
os.makedirs(log_folder, exist_ok=True)
file = log_folder + date_str + '.log'
file_handler = logging.FileHandler(file, mode='a')
file_handler.setLevel(log_level)

# formatter = logging.Formatter('%(filename)s:%(levelname)s:%(asctime)s:%(threadName)-10s:%(message)s')
formatter = logging.Formatter('%(filename)s:%(lineno)d:%(levelname)s:%(asctime)s:%(threadName)-10s:%(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add the handlers to the logger
logger.addHandler(file_handler)