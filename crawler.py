# -*- coding: utf-8 -*-
"""
Created on Fri Mar  6 15:39:21 2020

@author: liming
"""

from bs4 import BeautifulSoup
import re
import json
import time
import logging
import datetime
import requests
import pymongo
from flask import Flask
from flask import make_response
from urllib import parse
import const

headers = {
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 Safari/537.36'
}

mongodb_collection_news = 'news'
PORT = 8081

class MongoDBClient:
    def __init__(self):
        # 转义用户名和密码
        self.user = parse.quote_plus(const.mongodb_user)
        self.password = parse.quote_plus(const.mongodb_password)
        # 连接MongoDB
        self.client = pymongo.MongoClient(const.mongodb_url.format(self.user,self.password))
        self.db = self.client['covid19']
        
    def insert(self, collection, data):
        self.db[collection].insert(data)

    def find_one(self, collection, data=None):
        return self.db[collection].find_one(data)
    
class ResponseBody:
    def __init__(self,success,data):
        self.success = success #0成功 -1失败
        self.data = data

class News:        
    def __init__(self,crawl_time,key_word,title,author,img,publish_date,publish_time,category,description,article,link,origin):
        self.crawl_time = crawl_time
        self.key_word = key_word
        self.title = title
        self.author = author
        self.img = img
        self.publish_date = publish_date
        self.publish_time = publish_time
        self.category = category
        self.description = description
        self.article = article
        self.link = link
        self.origin = origin

class Crawler:
    def __init__(self):
        self.session = requests.session()
        self.session.headers.update(headers)
        self.crawl_timestamp = int()
        self.category = ''
#        self.mongodb = MongoDBClient()
    
    def run(self,category):
        self.crawl_timestamp = int(datetime.datetime.timestamp(datetime.datetime.now())*1000)
        try:
            response = self.session.get(url='https://opendata.baidu.com/api.php?query=%E5%85%A8%E5%9B%BD&resource_id=39258&tn=wisetpl&format=json')
            if response.status_code == 200:
                data = response.json()['data']
        except requests.exceptions.ChunkedEncodingError:
            print('error')
        
        self.category = category
        result = ResponseBody(success=0,data=self.data_parser(data = data,category=category))
        return json.dumps(result, default=lambda o: o.__dict__, sort_keys=True, indent=4)
        
    def data_parser(self,data,category):
        all_articles = []
        for data_list in data:
            for item in data_list['list']:
                if item['title'] == category:
                    for news in item['item']:
#                        n = News(self.crawl_timestamp,news['query'],None,self.crawl_timestamp,'新冠病毒','',news['query'],news['url'],'')
                        news_search_url = news['url']
#                        description = self.getDescription(news_search_url)
                        r = self.session.get(url=news_search_url).content
                        text = str(r,encoding='utf-8')
                        soup = BeautifulSoup(text, 'lxml')
                        description = soup.select_one('div.c-result-content div.c-line-clamp3')
                        if description:
                            description_1 = description.string
                        else:
                            description_1 = ''
                        img = soup.select_one('div.c-result-content div.timeline-head-position__2Xdnh img.c-img-img')
                        if img:
                            img_1 = img.attrs['src']
                        else:
                            img_1 = None
                        article_info_url = self.getArticleUrl(news_search_url)
                        if article_info_url:
                            article = self.getArticleInfo(article_info_url)
                            if article:
                                article.key_word = news['query']
                                article.description = description_1
                                article.img = img_1
                                #对象转json
                                #str_article = json.dumps(article, default=lambda o: o.__dict__, sort_keys=True, indent=4)
#                                print(str_article)
                                #all_articles = all_articles + str(str_article) + '\n'
#                                self.mongodb.insert(collection=mongodb_collection_news,data=article.__dict__)
                                all_articles.append(article)
                            else:
                                continue
            return all_articles
                        
    def getDescription(self,url):
        r = self.session.get(url=url).content
        text = str(r,encoding='utf-8')
        soup = BeautifulSoup(text, 'lxml')
        css = 'div.c-result-content div.c-line-clamp3'
        a = soup.select_one(css)
        return a.string
#        print(a.string)
        
    def getArticleUrl(self,url):
        r = self.session.get(url=url).content
        text = str(r,encoding='utf-8')
        soup = BeautifulSoup(text, 'lxml')
        css = 'div.c-result-content div.timeline-head-content__32zeO'
        a = soup.select_one(css)
        if a and 'rl-link-data-url' in a.div.attrs:
            return a.div.attrs['rl-link-data-url']
        else:
            return None
        
    def getArticleInfo(self,url):
        if not url:
            return
        r = self.session.get(url=url).content
        text = str(r,encoding='utf-8')
        soup = BeautifulSoup(text, 'lxml')
        title = soup.select_one('div.article-title')
        if title:
            title_1 = title.string
        else:
            return
        author = soup.select_one('div.article-desc p.author-name')
        if author:
            author_1 = author.string
        else:
            author_1 = '佚名'
        publish_date = soup.select_one('div.article-desc span.date')
        if publish_date:
            publish_date_1 = publish_date.string.replace('发布时间：','')
        else:
            publish_date_1 = ''
        publish_time = soup.select_one('div.article-desc span.time')
        if publish_time:
            publish_time_1 = publish_time.string
        else:
            publish_time_1 = ''
        content = soup.select_one('div.article-content')
        if content:
            content_1 = str(content)
        else:
            return
        return News(self.crawl_timestamp,None,title_1,author_1,None,publish_date_1,publish_time_1,self.category,'',content_1,url,None)
        
        
app = Flask(__name__)

@app.route('/news/<int:category_id>', methods=['GET'])
def getNews(category_id):
    enc = 'UTF-8'
    crawler = Crawler()
    if category_id == 0:
        category = '今日疫情热搜'
    elif category_id == 1:
        category = '防疫知识热搜'
    elif category_id == 2:
        category = '热搜谣言粉碎'
    elif category_id == 3:
        category = '复工复课热搜'
    else:
        return ''
    r = crawler.run(category=category)
    resp = make_response(r.encode(enc))
    resp.headers['Content-type'] = "application/json; charset=%s" % enc
    return resp

if __name__ == '__main__':
   app.run(debug=True)
##
#crawler = Crawler()
#r = crawler.run(category='今日疫情热搜')
#print(r)



        


        
        
        
        
        
        
        
