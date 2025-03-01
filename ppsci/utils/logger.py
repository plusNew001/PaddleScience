# Copyright (c) 2023 PaddlePaddle Authors. All Rights Reserved.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import functools
import logging
import os
import sys

import paddle.distributed as dist

_logger = None


def init_logger(name="ppsci", log_file=None, log_level=logging.INFO):
    """Initialize and get a logger by name.
    If the logger has not been initialized, this method will initialize the
    logger by adding one or two handlers, otherwise the initialized logger will
    be directly returned. During initialization, a StreamHandler will always be
    added. If `log_file` is specified a FileHandler will also be added.

    Args:
        name (str): Logger name.
        log_file (str | None): The log filename. If specified, a FileHandler
            will be added to the logger.
        log_level (int): The logger level. Note that only the process of
            rank 0 is affected, and other processes will set the level to
            "Error" thus be silent most of the time.
    Returns:
        logging.Logger: The expected logger.
    """
    if isinstance(log_level, str):
        log_level = getattr(logging, log_level.upper())

    global _logger

    # solve mutiple init issue when using paddlescience.py and engin.engin
    init_flag = False
    if _logger is None:
        _logger = logging.getLogger(name)
        init_flag = True

    formatter = logging.Formatter(
        "[%(asctime)s] %(name)s %(levelname)s: %(message)s", datefmt="%Y/%m/%d %H:%M:%S"
    )

    stream_handler = logging.StreamHandler(stream=sys.stdout)
    stream_handler.setFormatter(formatter)
    stream_handler._name = "stream_handler"

    # add stream_handler when _logger dose not contain stream_handler
    for i, h in enumerate(_logger.handlers):
        if h.get_name() == stream_handler.get_name():
            break
        if i == len(_logger.handlers) - 1:
            _logger.addHandler(stream_handler)
    if init_flag:
        _logger.addHandler(stream_handler)

    if log_file is not None and dist.get_rank() == 0:
        log_file_folder = os.path.split(log_file)[0]
        os.makedirs(log_file_folder, exist_ok=True)
        file_handler = logging.FileHandler(log_file, "a")
        file_handler.setFormatter(formatter)
        file_handler._name = "file_handler"

        # add file_handler when _logger dose not contain same file_handler
        for i, h in enumerate(_logger.handlers):
            if (
                h.get_name() == file_handler.get_name()
                and h.baseFilename == file_handler.baseFilename
            ):
                break
            if i == len(_logger.handlers) - 1:
                _logger.addHandler(file_handler)

    if dist.get_rank() == 0:
        _logger.setLevel(log_level)
    else:
        _logger.setLevel(logging.ERROR)
    _logger.propagate = False


def set_log_level(log_level):
    """Set log level."""
    if dist.get_rank() == 0:
        _logger.setLevel(log_level)
    else:
        _logger.setLevel(logging.ERROR)


def log_at_trainer0(log_func):
    """
    Logs will print multi-times when calling Fleet API.
    Only display single log and ignore the others.
    """

    @functools.wraps(log_func)
    def wrapped_log_func(fmt, *args):
        if dist.get_rank() == 0:
            log_func(fmt, *args)

    return wrapped_log_func


@log_at_trainer0
def info(fmt, *args):
    _logger.info(fmt, *args)


@log_at_trainer0
def debug(fmt, *args):
    _logger.debug(fmt, *args)


@log_at_trainer0
def warning(fmt, *args):
    _logger.warning(fmt, *args)


@log_at_trainer0
def error(fmt, *args):
    _logger.error(fmt, *args)


def scaler(name, value, step, vdl_writer=None, wandb_writer=None):
    """
    This function will draw a scalar curve generated by the visualdl.
    Usage: Install visualdl: pip3 install visualdl==2.0.0b4
           and then:
           visualdl --logdir ./scalar --host 0.0.0.0 --port 8830
           to preview loss corve in real time.
    """
    if vdl_writer is not None:
        vdl_writer.add_scalar(tag=name, step=step, value=value)
    if wandb_writer is not None:
        wandb_writer.log({"step": step, f"{name.replace('_', '/')}": value})


def advertise():
    """
    Show the advertising message like the following:

    ===========================================================
    ==      PaddleScience is powered by PaddlePaddle !       ==
    ===========================================================
    ==                                                       ==
    ==   For more info please go to the following website.   ==
    ==                                                       ==
    ==     https://github.com/PaddlePaddle/PaddleScience     ==
    ===========================================================

    """
    _copyright = "PaddleScience is powered by PaddlePaddle !"
    ad = "For more info please go to the following website."
    website = "https://github.com/PaddlePaddle/PaddleScience"
    AD_LEN = 6 + len(max([_copyright, ad, website], key=len))

    info(
        "\n{0}\n{1}\n{2}\n{3}\n{4}\n{5}\n{6}\n{7}\n".format(
            "=" * (AD_LEN + 4),
            "=={}==".format(_copyright.center(AD_LEN)),
            "=" * (AD_LEN + 4),
            "=={}==".format(" " * AD_LEN),
            "=={}==".format(ad.center(AD_LEN)),
            "=={}==".format(" " * AD_LEN),
            "=={}==".format(website.center(AD_LEN)),
            "=" * (AD_LEN + 4),
        )
    )
