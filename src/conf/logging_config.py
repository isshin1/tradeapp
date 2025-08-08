import logging
import logging.config
import yaml
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG_PATH = os.path.join(BASE_DIR, "conf", "config.yaml")

# Load config
with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)



date_str = str(datetime.now().today().date())
log_folder = BASE_DIR + '/data/logs/' + date_str.split('-')[0] + '/' + date_str.split('-')[1] + '/'
os.makedirs(log_folder, exist_ok=True)
dynamic_log_file = log_folder + date_str + '.log'

config["logging"]["handlers"]["file"]["filename"] = dynamic_log_file

logging.config.dictConfig(config["logging"])

logger = logging.getLogger(__name__)
logger.info("Application started with dynamic log file.")