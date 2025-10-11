import logging
import logging.config
import yaml
import os
from datetime import datetime
from conf.config import BASE_DIR
# Configuration paths
# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "conf", "config.yaml")


def setup_logging():
    """Setup logging with dynamic file paths and append mode - single file only"""
    try:
        # Load YAML configuration
        with open(CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f)

        # Create dynamic log paths
        date_str = str(datetime.now().date())
        year, month, day = date_str.split('-')
        log_folder = os.path.join(BASE_DIR, 'data', 'logs', year, month)
        os.makedirs(log_folder, exist_ok=True)

        # Update file paths in config - single file for everything
        dynamic_log_file = os.path.join(log_folder, f"{date_str}.log")
        config["logging"]["handlers"]["file"]["filename"] = dynamic_log_file

        # Ensure append mode is set
        config["logging"]["handlers"]["file"]["mode"] = "a"

        # Remove error_file handler if it exists (we're using single file now)
        if "error_file" in config["logging"]["handlers"]:
            del config["logging"]["handlers"]["error_file"]

        # Update root logger to only use console and single file handler
        if "loggers" in config["logging"] and "" in config["logging"]["loggers"]:
            config["logging"]["loggers"][""]["handlers"] = ["console", "file"]

        # Apply configuration
        logging.config.dictConfig(config["logging"])

        # Get logger and test
        logger = logging.getLogger(__name__)

        # Check if log file exists and log accordingly
        file_exists = os.path.exists(dynamic_log_file)
        if file_exists:
            logger.info(f"Logging resumed. Appending to existing log file: {dynamic_log_file}")
        else:
            logger.info(f"Logging initialized. New log file created: {dynamic_log_file}")

        return logger

    except FileNotFoundError:
        print(f"Config file not found: {CONFIG_PATH}")
        # Fallback with append mode - single file
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s] [%(levelname)s] (%(filename)s:%(lineno)d) %(message)s',
            handlers=[
                logging.FileHandler(f'fallback-{datetime.now().date()}.log', mode='a'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)

    except Exception as e:
        print(f"Error setting up logging: {e}")
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(__name__)


def setup_logging_programmatic():
    """Alternative: Setup logging programmatically with single file in append mode"""
    try:
        # Create dynamic log paths
        date_str = str(datetime.now().date())
        year, month, day = date_str.split('-')
        log_folder = os.path.join(BASE_DIR, 'data', 'logs', year, month)
        os.makedirs(log_folder, exist_ok=True)

        dynamic_log_file = os.path.join(log_folder, f"{date_str}_feed.log")

        # Configure logging programmatically - single file for everything
        logging_config = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'detailed': {
                    # Updated format to include filename and line number
                    'format': '[%(asctime)s] [%(levelname)s] (%(filename)s:%(lineno)d) %(funcName)s() - %(message)s',
                    'datefmt': '%Y-%m-%d %H:%M:%S'
                },
                'simple': {
                    # Also include filename and line number in console output
                    'format': '[%(levelname)s] (%(filename)s:%(lineno)d) %(message)s'
                }
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'level': 'INFO',
                    'formatter': 'simple',
                    'stream': 'ext://sys.stdout'
                },
                'file': {
                    'class': 'logging.FileHandler',
                    'level': 'DEBUG',  # Log everything from DEBUG level up
                    'formatter': 'detailed',
                    'filename': dynamic_log_file,
                    'mode': 'a',  # Explicitly set append mode
                    'encoding': 'utf-8'
                }
            },
            'loggers': {
                '': {  # Root logger
                    'level': 'INFO',  # Changed from 'DEBUG'
                    'handlers': ['console', 'file'],
                    'propagate': False
                },
                'urllib3': {
                    'level': 'WARNING',
                    'handlers': ['console', 'file'],
                    'propagate': False
                },
                'urllib3.connectionpool': {
                    'level': 'WARNING',
                    'handlers': ['console', 'file'],
                    'propagate': False
                }
            }
        }

        logging.config.dictConfig(logging_config)

        logger = logging.getLogger(__name__)

        # Check if log file exists and log accordingly
        file_exists = os.path.exists(dynamic_log_file)
        if file_exists:
            logger.info(f"Logging resumed. Appending to existing log file: {dynamic_log_file}")
        else:
            logger.info(f"Logging initialized. New log file created: {dynamic_log_file}")

        return logger

    except Exception as e:
        print(f"Error setting up programmatic logging: {e}")
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(__name__)


def demonstrate_logging():
    """Demonstrate logging with filename and line numbers - all to single file"""
    logger = logging.getLogger(__name__)

    logger.debug("This is a debug message - goes to single file")
    logger.info("This is an info message - goes to single file")
    logger.warning("This is a warning message - goes to single file")
    logger.error("This is an error message - goes to single file")
    logger.critical("This is a critical message - goes to single file")

    # Demonstrate exception logging - also goes to single file
    try:
        result = 10 / 0
    except ZeroDivisionError as e:
        logger.exception("Exception occurred: %s", str(e))

    # Demonstrate logging from different functions
    another_function()


def another_function():
    """Another function to show different line numbers - all to single file"""
    logger = logging.getLogger(__name__)
    logger.info("Message from another_function() - single file")
    nested_function()


def nested_function():
    """Nested function to demonstrate call stack - all to single file"""
    logger = logging.getLogger(__name__)
    logger.warning("Warning from nested_function() - all levels in single file!")


def test_append_behavior():
    """Test that logs are actually appending to single file"""
    logger = logging.getLogger(__name__)

    for i in range(3):
        logger.info(f"Test append message {i + 1} - All messages in single file")
        logger.error(f"Test error message {i + 1} - Errors also in same single file")


# Initialize logging when module is imported
# Use the programmatic version for guaranteed single file append mode
logger = setup_logging_programmatic()

if __name__ == "__main__":
    demonstrate_logging()
    print("\n" + "=" * 50)
    print("Testing append behavior...")
    test_append_behavior()
    print("Check your single log file - all messages should be appended together!")