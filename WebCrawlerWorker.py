import os

import Log
import WebCrawlerModules

logger = Log.LoggerHandler(name="WebCrawlerWorker")


class WebCrawlerWorker:
    def __init__(self, exercise_id, path, cookie, progress_callback=None):
        self.id = exercise_id
        self.header = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/70.0.3538.102 Safari/537.36'}

        self.cookie = cookie
        self.path = path
        self.__init_folder_configure()
        # 题解与练习的爬虫
        self.crawler_worker = WebCrawlerModules.CrawlerWorker(self.path, self.id, self.header, self.cookie,
                                                              progress_callback)

    def __init_folder_configure(self):
        if not os.path.exists(self.path):
            # 如果文件夹不存在，使用os.mkdir创建它
            os.mkdir(self.path)
            # logger.info(f"文件夹 '{self.path}' 已创建")

    def start_work(self):

        if self.crawler_worker.get_exercise() != -1:
            self.crawler_worker.get_solution()
