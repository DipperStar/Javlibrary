import requests
from bs4 import BeautifulSoup
from urllib import parse
import urllib3
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import pandas as pd
from retrying import retry
import threading
import string
from mongo import MongoDB

urllib3.disable_warnings()

class JavLib(object):
    def __init__(self, mode = 'bestrated'):
        self.mode = mode
        self.cookie = ''
        self.url = 'http://www.p26y.com/cn/'
        self.torrent_url = 'https://www.bturl.at/search/'
        self.video = {}
        self.headers = {'Cookie': self.cookie, 
                        'Host': 'www.p26y.com',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.75 Safari/537.36',
                        'If-None-Match': 'W/"3a18de34b39581014d560cc3522a80b7"',
                        'If-Modified-Since': 'Tue, 22 Jan 2019 00:00:00 GMT',
                        'Connection': 'keep-alive',
                        'Cache-Control': 'max-age=0',
                        'Accept-Language': 'zh-CN,zh;q=0.9',
                        'Upgrade-Insecure-Requests': '1',
                        'Accept-Encoding': 'gzip, deflate'
                        }
        self.girlsnamedb = MongoDB('Javdb', 'girlsname')
        self.rankdb = MongoDB('Javdb', 'rankdb')

    def get_cookie(self, now_url):
        '''
        刷新页面cookie
        '''
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
        '''
        根据番号identity获取磁力链接
        '''
        torrent_url = parse.urljoin(self.torrent_url, identity+'_ctime_1.html')
        print(torrent_url)
        resp = requests.get(torrent_url, verify = False)
        soup = BeautifulSoup(resp.content, 'html.parser')
        tags = soup.find_all('li')
        if identity not in self.video:
            self.video[identity] = {'title': 'null', 'score': 'null'}
        self.video[identity].update({'torrent': [(tag.a.text.strip(), tag.a['href'][1:-5], tag.span.text, tag.find_all('span', limit = 2)[1].text) for tag in tags if '@' not in tag.a.text.strip()]})

    @retry
    def spider(self, now_url):
        '''
        作品页爬虫
        '''
        resp = requests.get(now_url, headers = self.headers, verify = False)
        self.soup_video(resp)

    def soup_video(self, resp):
        '''
        作品页面解析，得到评分，题目，番号，存入self.video
        '''
        soup = BeautifulSoup(resp.content, 'html.parser')
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

    def rank(self):
        '''
        获取排行榜作品
        '''
        thread_list = []
        dic_mode = {'bestrated': 'http://www.p26y.com/cn/vl_bestrated.php?list&page={}', 'mostwanted': 'vl_mostwanted.php?list&page={}'} # 最高评价,最受期待
        real_url = parse.urljoin(self.url, dic_mode[self.mode])
        self.get_cookie(self.url)
        for pages in range(1, 11):  # 获取排行榜前10页作品信息
            now_url = real_url.format(pages)
            self.spider(now_url)

        thread_list = []
        for identity in self.video:  # 根据番号查找磁力链接
            thread = threading.Thread(target = self.torrent, args = (identity,))
            thread.start()
            thread_list.append(thread)

        for thread in thread_list:
            thread.join()

        for identity in self.video:  # 存入数据库db['Javdb']['girlsname']
            for torrent in self.video[identity]['torrent']:
                torrent_name = torrent[0]
                torrent_href = torrent[1]
                torrent_time = torrent[2]
                torrent_memory = torrent[3]
                print(torrent_name, torrent_href)
                self.rankdb.update({'identity': identity,
                                        'title': self.video[identity]['title'],
                                        'score': self.video[identity]['score'],  
                                        'torrent_name': torrent_name, 
                                        'torrent_href': torrent_href,
                                        'torrent_time': torrent_time,
                                        'torrent_memory': torrent_memory}, True)

    def girls(self):
        '''
        更新演员名录，存入数据库db['Javdb']['girlsname']
        '''
        url_name = parse.urljoin(self.url, 'star_list.php?prefix={}&page=1')
        alphabet = list(string.ascii_uppercase)
        for character in alphabet:
            url = url_name.format(character)
            self.get_cookie(url)
            self.girls_spider(url)
        return 0
            
    @retry
    def girls_spider(self, url):
        '''
        演员名录页爬虫
        '''
        print (url)
        resp = requests.get(url, headers = self.headers)
        soup = BeautifulSoup(resp.content, 'lxml')
        searchitem = soup.find_all('div', class_ = 'searchitem')
        for girl in searchitem:
            print(girl.a.text, girl['id'], self.girlsnamedb.update({'girls': girl.a.text, 'code': girl['id']}, upsert = True))

        if soup.find_all('a', class_ = 'page next'):
            next_page = soup.find_all('a', class_ = 'page next')[0]['href']
            next_url = parse.urljoin(self.url, next_page)
            self.girls_spider(next_url)
        else:
            return 0

    def write_down(self, data, filename = 'javlib'):
        '''
        将数据(字典列表)输出到excel
        '''
        df = pd.DataFrame(data)
        df.to_excel('{}.xlsx'.format(filename), index = True)

if __name__ == '__main__':
    jav = JavLib()
    jav.rank()