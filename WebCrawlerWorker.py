import os
import WebCrawlerModules


class WebCrawlerWorker:
    def __init__(self, exercise_id, path, cookie, progress_callback=None):
        self.id = exercise_id
        self.header = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/70.0.3538.102 Safari/537.36'}
        self.cookie = cookie

        self.path = path
        self.init_folder_configure()

        # 题解与练习的爬虫
        self.crawler_worker = WebCrawlerModules.CrawlerWorker(self.path, self.id, self.header, self.cookie,
                                                              progress_callback)

    def init_folder_configure(self):
        if not os.path.exists(self.path):
            # 如果文件夹不存在，使用os.mkdir创建它
            os.mkdir(self.path)
            print(f"文件夹 '{self.path}' 已创建")
        else:
            print(f"文件夹 '{self.path}' 已存在")

    def start_work(self):
        self.crawler_worker.get_exercise()
        self.crawler_worker.get_solution()
