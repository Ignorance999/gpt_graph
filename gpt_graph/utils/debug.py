import logging
import functools
import os
import datetime
from dataclasses import is_dataclass, asdict

# Configure a specific logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set the desired level for the logger

# Create console handler with a specific log level
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)  # Set the desired level for the console handler
# ch.stream.encoding = 'utf-8'

log_directory = r"../../outputs/logs"
os.makedirs(log_directory, exist_ok=True)
timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
log_file_name = f"log_{timestamp}.txt"
log_file_path = os.path.join(log_directory, log_file_name)

fh = logging.FileHandler(log_file_path, encoding="utf-8")
fh.setLevel(logging.DEBUG)


# Create formatter and add it to the handler
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
fh.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(ch)
logger.addHandler(fh)


def logger_debug(*args):
    target_length = 300

    def format_arg(arg):
        if isinstance(arg, str):
            return (
                f"{arg[:target_length-3]}...({len(arg)}chars)"
                if len(arg) > target_length
                else arg
            )
        elif isinstance(arg, dict):
            return {key: format_arg(value) for key, value in arg.items()}
        elif isinstance(arg, (list, tuple, set)):
            return type(arg)(format_arg(item) for item in arg)
        elif is_dataclass(arg):
            return format_arg(
                asdict(arg)
            )  # Convert the dataclass to a dict and format it
        else:
            arg_str = str(arg)
            return (
                f"{arg_str[:target_length-3]}...({len(arg_str)}chars)"
                if len(arg_str) > target_length
                else arg_str
            )

    formatted_args = (str(format_arg(arg)) for arg in args)
    # Join the formatted arguments with a ' - ' separator
    # NOTE: comment the follo0wing to avoid output yet. logger.debug(' - '.join(formatted_args))


# @debug
def debug(func):
    """Decorator to print the function details and arguments except 'self'."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # We skip 'self' if it exists by starting from the second argument
        args_repr = (
            [repr(a) for a in args[1:]]
            if "self" in func.__code__.co_varnames
            else [repr(a) for a in args]
        )
        kwargs_repr = [f"{k}={v}" for k, v in kwargs.items()]
        signature = ", ".join(args_repr + kwargs_repr)
        logger_debug(f"Calling {func.__module__}.{func.__name__}({signature})")
        value = func(*args, **kwargs)
        logger_debug(f"{func.__module__}.{func.__name__!r} returned {value!r}")
        return value

    return wrapper
