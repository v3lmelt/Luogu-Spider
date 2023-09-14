# Logger 模块的基本封装来源：https://blog.csdn.net/weixin_43635231/article/details/110745593
# Respect!

import logging
import colorlog


class LoggerHandler:

    def __init__(self,
                 name="root",
                 level='DEBUG',
                 file=None,
                 ):
        log_colors_config = {
            'DEBUG': 'white',  # cyan white
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'bold_red',
        }
        logger = logging.getLogger(name)
        # 设置级别
        logger.setLevel(level)

        file_formatter = logging.Formatter(
            fmt='[%(asctime)s.%(msecs)03d] %(filename)s -> %(funcName)s line:%(lineno)d [%(levelname)s] : %(message)s',
            datefmt='%Y-%m-%d  %H:%M:%S'
        )

        console_formatter = colorlog.ColoredFormatter(
            fmt='%(log_color)s[%(asctime)s.%(msecs)03d] %(filename)s -> %(funcName)s line:%(lineno)d [%(levelname)s] '
                ': %(message)s',
            datefmt='%Y-%m-%d  %H:%M:%S',
            log_colors=log_colors_config
        )

        # 初始化处理器
        if file:
            file_handle = logging.FileHandler(file)
            file_handle.setLevel(level)

            logger.addHandler(file_handle)
            file_handle.setFormatter(file_formatter)
        stream_handler = logging.StreamHandler()

        # 设置handle 的级别
        stream_handler.setLevel(level)

        logger.addHandler(stream_handler)
        stream_handler.setFormatter(console_formatter)

        self.logger = logger

    def debug(self, msg):
        return self.logger.debug(msg)

    def error(self, msg):
        return self.logger.error(msg)

    def critical(self, msg):
        return self.logger.critical(msg)

    def info(self, msg):
        return self.logger.info(msg)
