import unittest

import requests
import Utils
from bs4 import BeautifulSoup


class QueryLuoguList:
    def __init__(self, keyword, difficulty, tag, type):
        self.url = 'https://www.luogu.com.cn/problem/list?page=1'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/'
                          '537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36'
        }
        self.cookie = {
            '__client_id': '1d9dc4c15ef13440c22d357bcde61b47ce930088',
            '_uid': '87731'
        }
        self.result_name = []
        self.result_id = []

        self.query_param = {
            'keyword': keyword,
            'difficulty': difficulty,
            'tag': tag,
            'type': type,
        }

    def search_with_params(self):
        r = requests.get(self.url, headers=self.headers, cookies=self.cookie, params=self.query_param)
        if r.status_code == 200:
            soup = BeautifulSoup(r.content, 'lxml')
            decoded_json = Utils.uri_component_decoder(soup)
            data = Utils.json_parser(decoded_json)

            for item in data['currentData']['problems']['result']:
                self.result_name.append(item['title'])
                self.result_id.append(item['pid'])
                # print(self.result_name)
                # print(self.result_id)

    def get_result_name(self):
        return self.result_name

    def get_result_id(self):
        return self.result_id


class TestUtils(unittest.TestCase):
    def test_search_with_params(self):
        self.assertEqual(QueryLuoguList().search_with_params(), "")

    def test_search_with_params_complex(self):
        self.assertEqual(QueryLuoguList(keyword="", difficulty="2", tag="15|83", type="P").search_with_params(), "")
