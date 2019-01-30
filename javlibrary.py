import string
import time
from urllib import parse

import pandas as pd
import requests
import urllib3
from bs4 import BeautifulSoup
from retrying import retry
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from Threads import MyThread
from mongo import MongoDB

urllib3.disable_warnings()


class JavLib(object):
    def __init__(self):
        self.cookie = ''
        self.url = 'http://www.p26y.com/cn/'
        self.torrent_url = 'https://www.bturl.at/search/'
        self.video = {}
        self.headers = {'Cookie': self.cookie,
                        'Host': 'www.p26y.com',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,'
                                  '*/*;q=0.8',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, '
                                      'like Gecko) Chrome/68.0.3440.75 Safari/537.36',
                        'If-None-Match': 'W/"3a18de34b39581014d560cc3522a80b7"',
                        'If-Modified-Since': 'Tue, 22 Jan 2019 00:00:00 GMT',
                        'Connection': 'keep-alive',
                        'Cache-Control': 'max-age=0',
                        'Accept-Language': 'zh-CN,zh;q=0.9',
                        'Upgrade-Insecure-Requests': '1',
                        'Accept-Encoding': 'gzip, deflate'
                        }
        self.allgirls = MongoDB('Javdb', 'girlsname')  # 所有girl名称—>页面编码键值对
        self.rankdb = MongoDB('Javdb', 'rankdb')  # 最受受欢迎作品榜单
        self.girlsindexdb = MongoDB('Javdb', 'girlsindexdb')  # 单个girl的所有作品db

    def get_cookie(self, now_url):
        """
        刷新页面cookie，存入self.cookie
        :now_url:需获取cookie的url
        """
        self.cookie = ''
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        browser = webdriver.Chrome(options=chrome_options)
        browser.implicitly_wait(30)
        browser.set_page_load_timeout(30)
        browser.get(now_url)
        time.sleep(10)
        for keys in browser.get_cookies():
            self.cookie += '='.join([keys['name'], keys['value']]) + '; '
        browser.close()
        self.headers['cookie'] = self.cookie

    @retry
    def torrent(self, identity):
        """
        根据番号identity获取磁力链接，按照标准格式存入self.video,单独使用时缺少title和score
        :identity:作品番号
        """
        torrent_url = parse.urljoin(self.torrent_url, identity + '_ctime_1.html')
        print(torrent_url)
        resp = requests.get(torrent_url, verify=False)
        soup = BeautifulSoup(resp.content, 'lxml')
        tags = soup.find_all('li')
        dic_torrent = {}
        dic_torrent[identity] = []
        for tag in tags:
            dic_torrent[identity].append({'torrent_name': tag.a.text.strip(),
                                          'torrent_href': tag.a['href'][1:-5],
                                          'torrent_time': tag.span.text,
                                          'torrent_memory': tag.find_all('span', limit=2)[1].text
                                          })
        return dic_torrent

    @retry
    def spider(self, now_url):
        """
        作品页爬虫,调用soup_video获得作品信息
        :now_url:作品页地址
        """
        resp = requests.get(now_url, headers=self.headers, verify=False)
        self.soup_spider(resp)

    @retry
    def allgirls_spider(self, url):
        """
        演员名录页爬虫
        """
        print(url)
        resp = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(resp.content, 'lxml')
        searchitem = soup.find_all('div', class_='searchitem')
        for girl in searchitem:
            print(girl.a.text, girl['id'], self.allgirls.update({'girls': girl.a.text, 'code': girl['id']}, upsert=True))

        if soup.find_all('a', class_='page next'):
            next_page = soup.find_all('a', class_='page next')[0]['href']
            next_url = parse.urljoin(self.url, next_page)
            self.allgirls_spider(next_url)
        else:
            return 0

    def soup_spider(self, resp):
        """
        作品页面解析，得到评分，题目，番号，存入self.video
        :param resp: 作品页response
        :return:返回identity, score, title
        """
        soup = BeautifulSoup(resp.content, 'lxml')
        tags = soup.find_all('tr')
        for tag in tags:
            try:
                score = tag.find_all('td')[1].text
                title = tag.td.find_all('a')[-1]['title']
            except:
                continue
            print(title)
            identity = title.split(' ')[0]
            self.video[identity] = {'score': score, 'title': title}

    @retry
    def soup_girlindex(self, url, girl):
        """
        单个girl的作品目录解析，得到文章数，评论数，番号，标题，存入girlsindexdb
        :param url:girl作品目录的url
        :return:存入girlsindexdb
        """
        resp = requests.get(url, headers=self.headers, verify=False)
        soup = BeautifulSoup(resp.content, 'html.parser')
        tags = soup.find_all('tr')
        thread_list = []
        for tag in tags:
            thread = MyThread(self.thread_grilindex, args=(tag, girl,))
            thread.start()
            thread_list.append(thread)


        for thread in thread_list:
            thread.join()

        if soup.find_all('a', class_='page next'):
            next_page = soup.find_all('a', class_='page next')[0]['href']
            next_url = parse.urljoin(self.url, next_page)
            self.soup_girlindex(next_url, girl)
        else:
            return 0

    def thread_grilindex(self, tag, girl):
        try:
            date, article, replies = [i.text for i in tag.find_all('td')[1:]]
            article = int(article)
            replies = int(replies)
            title = tag.td.find_all('a')[-1]['title']
        except:
            return
        print(title)
        identity = title.split(' ')[0]
        dic_torrent = self.torrent(identity)
        for torrent in dic_torrent[identity]:
            torrent_name = torrent['torrent_name']
            torrent_href = torrent['torrent_href']
            torrent_time = torrent['torrent_time']
            torrent_memory = torrent['torrent_memory']
            self.girlsindexdb.update({'girl': girl, 'title': title,
                                      'date': date, 'article': article,
                                      'replies': replies, 'torrent_name': torrent_name,
                                      'torrent_href': torrent_href, 'torrent_memory': torrent_memory,
                                      'torrent_time': torrent_time
                                      }, upsert=True)

    def rank(self, mode='bestrated'):
        """
        获取排行榜作品
        """
        dic_mode = {'bestrated': 'http://www.p26y.com/cn/vl_bestrated.php?list&page={}',
                    'mostwanted': 'vl_mostwanted.php?list&page={}'}  # 最高评价,最受期待
        real_url = parse.urljoin(self.url, dic_mode[mode])
        self.get_cookie(self.url)
        for pages in range(1, 11):  # 获取排行榜前10页作品信息
            now_url = real_url.format(pages)
            self.spider(now_url)

        thread_list = []
        for identity in self.video:  # 根据番号查找磁力链接
            thread = MyThread(self.torrent, args=(identity,))
            thread.start()
            thread_list.append(thread)

        dic_torrent = {}
        for thread in thread_list:
            thread.join()
            dic_torrent.update(thread.get_result())

        for identity in self.video:  # 存入数据库self.allgirls
            for torrent in dic_torrent[identity]:
                torrent_name = torrent['torrent_name']
                torrent_href = torrent['torrent_href']
                torrent_time = torrent['torrent_time']
                torrent_memory = torrent['torrent_memory']
                print(torrent_name, torrent_href)
                self.rankdb.update({'identity': identity,
                                    'title': self.video[identity]['title'],
                                    'score': self.video[identity]['score'],
                                    'torrent_name': torrent_name,
                                    'torrent_href': torrent_href,
                                    'torrent_time': torrent_time,
                                    'torrent_memory': torrent_memory}, True)

    def girlindex(self, girl):
        """
        爬指定girl的所有作品，存入数据库self.girlsindexdb
        :return:
        """
        self.girlcode = [girls['code'] for girls in self.allgirls.find({'girls': girl})]
        for code in self.girlcode:
            url = 'http://www.p26y.com/cn/vl_star.php?list&s={}'.format(code)
            self.get_cookie(url)
            self.soup_girlindex(url, girl)

    def allgirls(self):
        """
        更新演员名录，存入数据库db['Javdb']['girlsname'],仅用于更新名录
        """
        url_name = parse.urljoin(self.url, 'star_list.php?prefix={}&page=1')
        alphabet = list(string.ascii_uppercase)
        for character in alphabet:
            url = url_name.format(character)
            self.get_cookie(url)
            self.allgirls_spider(url)
        return 0

    def write_down(self, data, filename='javlib'):
        """
        将数据(字典列表)输出到excel
        """
        df = pd.DataFrame(data)
        df.to_excel('{}.xlsx'.format(filename), index=True)


if __name__ == '__main__':
    jav = JavLib()