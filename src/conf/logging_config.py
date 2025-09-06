import logging
import logging.config
import yaml
import os
from datetime import datetime

# Configuration paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "conf", "config.yaml")


def setup_logging():
    """Setup logging with dynamic file paths"""
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

        # If you added the error_file handler, update it too
        if "error_file" in config["logging"]["handlers"]:
            error_log_file = os.path.join(log_folder, f"error-{date_str}.log")
            config["logging"]["handlers"]["error_file"]["filename"] = error_log_file

        # Apply configuration
        logging.config.dictConfig(config["logging"])

        # Get logger and test
        logger = logging.getLogger(__name__)
        logger.info(f"Logging initialized. Log file: {dynamic_log_file}")

        return logger

    except FileNotFoundError:
        print(f"Config file not found: {CONFIG_PATH}")
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s] [%(levelname)s] (%(filename)s:%(lineno)d) %(message)s'
        )
        return logging.getLogger(__name__)

    except Exception as e:
        print(f"Error setting up logging: {e}")
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


# Initialize logging when module is imported
logger = setup_logging()

# if __name__ == "__main__":
#     demonstrate_logging()