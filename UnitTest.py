import unittest
import tkinter as tk
from tkinter import filedialog
from unittest.mock import patch
from UserInterface import select_path, start_crawling


class TestUserInterface(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tk.Tk()

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    @patch("tkinter.filedialog.askdirectory", return_value="F:/Test_Path")
    def test_ui_start_crawling(self, mock_filedialog):
        exercise_id = "5615"
        num_of_exercises = "5"
        thread_num = "1"

        # 模拟用户输入
        with patch("UserInterface.exercise_id_entry.get", return_value=exercise_id), \
                patch("UserInterface.num_of_exercises_entry.get", return_value=num_of_exercises), \
                patch("UserInterface.thread_num_entry.get", return_value=thread_num), \
                patch("UserInterface.path_entry.get", return_value="F:/Test_Path"):
            # 模拟选择路径按钮点击
            select_path()

            # 模拟开始按钮点击
            start_crawling()

        # 此处添加等待爬取完成的代码或断言


if __name__ == '__main__':
    unittest.main()
