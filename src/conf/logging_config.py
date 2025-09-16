import logging
import logging.config
import yaml
import os
from datetime import datetime

# Configuration paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "conf", "config.yaml")


def setup_logging():
    """Setup logging with dynamic file paths and append mode"""
    try:
        # Load YAML configuration
        with open(CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f)

        # Create dynamic log paths
        date_str = str(datetime.now().date())
        year, month, day = date_str.split('-')
        log_folder = os.path.join(BASE_DIR, 'data', 'logs', year, month)
        os.makedirs(log_folder, exist_ok=True)

        # Update file paths in config
        dynamic_log_file = os.path.join(log_folder, f"{date_str}.log")
        config["logging"]["handlers"]["file"]["filename"] = dynamic_log_file

        # Ensure append mode is set
        if "mode" not in config["logging"]["handlers"]["file"]:
            config["logging"]["handlers"]["file"]["mode"] = "a"

        # If you added the error_file handler, update it too
        if "error_file" in config["logging"]["handlers"]:
            error_log_file = os.path.join(log_folder, f"error-{date_str}.log")
            config["logging"]["handlers"]["error_file"]["filename"] = error_log_file
            # Ensure append mode for error file too
            if "mode" not in config["logging"]["handlers"]["error_file"]:
                config["logging"]["handlers"]["error_file"]["mode"] = "a"

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
        # Fallback with append mode
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
    """Alternative: Setup logging programmatically with guaranteed append mode"""
    try:
        # Create dynamic log paths
        date_str = str(datetime.now().date())
        year, month, day = date_str.split('-')
        log_folder = os.path.join(BASE_DIR, 'data', 'logs', year, month)
        os.makedirs(log_folder, exist_ok=True)

        dynamic_log_file = os.path.join(log_folder, f"{date_str}.log")
        error_log_file = os.path.join(log_folder, f"error-{date_str}.log")

        # Configure logging programmatically
        logging_config = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'detailed': {
                    'format': '[%(asctime)s] [%(levelname)s] (%(filename)s:%(lineno)d) %(funcName)s() - %(message)s',
                    'datefmt': '%Y-%m-%d %H:%M:%S'
                },
                'simple': {
                    'format': '[%(levelname)s] %(message)s'
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
                    'level': 'DEBUG',
                    'formatter': 'detailed',
                    'filename': dynamic_log_file,
                    'mode': 'a',  # Explicitly set append mode
                    'encoding': 'utf-8'
                },
                'error_file': {
                    'class': 'logging.FileHandler',
                    'level': 'ERROR',
                    'formatter': 'detailed',
                    'filename': error_log_file,
                    'mode': 'a',  # Explicitly set append mode
                    'encoding': 'utf-8'
                }
            },
            'loggers': {
                '': {  # Root logger
                    'level': 'DEBUG',
                    'handlers': ['console', 'file', 'error_file'],
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
    """Demonstrate logging with filename and line numbers"""
    logger = logging.getLogger(__name__)

    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")

    # Demonstrate exception logging
    try:
        result = 10 / 0
    except ZeroDivisionError as e:
        logger.exception("Exception occurred: %s", str(e))

    # Demonstrate logging from different functions
    another_function()


def another_function():
    """Another function to show different line numbers"""
    logger = logging.getLogger(__name__)
    logger.info("Message from another_function()")
    nested_function()


def nested_function():
    """Nested function to demonstrate call stack"""
    logger = logging.getLogger(__name__)
    logger.warning("Warning from nested_function() - you can see the exact line!")


def test_append_behavior():
    """Test that logs are actually appending"""
    logger = logging.getLogger(__name__)

    for i in range(3):
        logger.info(f"Test append message {i + 1} - This should append to existing file")


# Initialize logging when module is imported
# Use the programmatic version for guaranteed append mode
logger = setup_logging_programmatic()

if __name__ == "__main__":
    demonstrate_logging()
    print("\n" + "=" * 50)
    print("Testing append behavior...")
    test_append_behavior()
    print("Check your log files - messages should be appended!")