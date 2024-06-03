import logging
import json
import time
import sys

import mechanicalsoup as ms
from ratelimiter import RateLimiter
from database import Forum, Category, Page, Topic, Post, Base
from urlpath import URL
from sqlalchemy import select
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def find_topic_query(category_id, topic_id):
    return select(Topic.id).where(Topic.category_id ==category_id).where(Topic.topic_id == topic_id)
    
def find_post_query(post_id, topic_id):
    return select(Post.id).where(Post.post_id==post_id).where(Post.topic_id == topic_id)

class RLBrowser(ms.StatefulBrowser):
    def __init__(self, rl: RateLimiter, *args, **kwargs):
        ms.StatefulBrowser.__init__(self, *args, **kwargs)
        self.rl = rl

    def get(self, *args, **kwargs):
        with self.rl:
            return ms.StatefulBrowser.get(self, *args, **kwargs)


def limited(until):
    duration = int(round(until - time.time()))
    logging.info('Rate limited, sleeping for {:d} seconds'.format(duration))


class DiscourseCrawler:
    def __init__(self, url: str, db: str):
        self.session = None
        self.browser = None
        self.base_url = None
        self.url = url
        self.db = db

    def create_db(self):
        engine = create_engine(self.db, echo=True, future=True)
        Base.metadata.create_all(engine)

    def crawl(self, echo=True):
        # Create db engine and open a session
        engine = create_engine(self.db, echo=echo, future=True)
        session_class = sessionmaker(bind=engine)
        self.session = session_class()
        
        # Prepare for crawling
        rate_limiter = RateLimiter(max_calls=3, period=1, callback=limited)
        self.browser = RLBrowser(rate_limiter)
        forum = self.get_forum()
        self.crawl_forum(forum)
        
    def get_forum(self):
        # Check if the forum we are going to crawl is in the database
        stmt = select(Forum).where(Forum.url == self.url)
        forum = self.session.scalars(stmt).first()
        print(forum)
        if forum is None:
            forum = Forum(url=self.url)
            self.session.add(forum)
            self.session.commit()
        return forum

    def crawl_forum(self, f: Forum):
        logging.info("Started crawling forum"+f.url)
        if not f.categories_crawled:
            resp = self.browser.get(URL(f.url) / "categories.json")
            category_list = json.loads(resp.content)["category_list"]
            logging.info("Categories: "+str(category_list.keys()))
            categories = category_list["categories"]
            for cat in categories:
                c = Category(category_id=cat["id"], forum_id=f.id, topic_url=cat["topic_url"], json=json.dumps(cat))
                self.session.add(c)
            f.categories_crawled = True
            self.session.commit()
            logging.info("Categories committed to db")
        else: 
            logging.info("Skipping obtaining the categories of the forum")
        
        self.crawl_categories(f)
        self.crawl_topics(f)
        logging.info("Finished crawling forum "+f.url)

    def crawl_categories(self,f: Forum):
        for c in f.categories:
            self.crawl_category(c)
            
    def crawl_category(self, c: Category):
        logging.info("Crawling category "+str(c.category_id))
        if not c.pages_crawled:
            query = select(Page) \
                .where(Page.category_id == c.id) \
                .order_by(Page.page_id.desc())
            last_page = self.session.execute(query).first()
            if last_page is not None:
                last_page = last_page[0]
            logging.debug(last_page)
            while (last_page is None) or (last_page.more_topics_url is not None):
                if last_page is None:
                    url = (URL(c.forum.url) / ("/c/" + str(c.category_id) + ".json")).with_query({"page": 0})
                    next_page_id = 0
                else:
                    next_page_id = last_page.page_id + 1
                    more_url = last_page.more_topics_url.replace("?", ".json?")
                    url = (URL(c.forum.url) / more_url)
                logging.info("Crawling page " + str(next_page_id))
                logging.debug("URL:"+str(url))
                resp = self.browser.get(url)
                json_page = json.loads(resp.content)
                #print(len(resp.content))
                #raise Expception("kk")
                topic_list = json_page["topic_list"]
                more_topics_url = topic_list["more_topics_url"] if "more_topics_url" in topic_list else None
                p = Page(category_id=c.id,
                         page_id=next_page_id,
                         more_topics_url=more_topics_url,
                         json=json.dumps(json_page))
                self.session.add(p)
                #this_page_topics = []
                for topic in topic_list["topics"]:
                    if self.session.execute(find_topic_query(c.id, topic["id"])).first() is None:
                        t = Topic(topic_id=topic["id"], category_id=c.id, page_excerpt_json=json.dumps(topic))
                        #this_page_topics.append(t)           
                        self.session.add(t)
                self.session.commit()
                logging.info("Page "+str(next_page_id)+" and their topics committed to db")
                logging.info("Started crawling the topics in this page")
                #for t in this_page_topics:
                #    self.crawl_topic(t)
                last_page = p
            c.pages_crawled = True
            self.session.commit()
            logging.info("Finished crawling category "+str(c.category_id))
        else:
            logging.info("Category "+str(c.category_id)+" has already been crawled")

    def crawl_topics(self, f: Forum):
        query = select(Topic).join(Topic.category).join(Category.forum).where(Forum.id==f.id).order_by(Topic.topic_id.desc())
        topics = self.session.scalars(query)
        for t in topics:
            self.crawl_topic(t)  
            
    def crawl_topic(self, t: Topic):
        logging.info("Crawling topic "+str(t.topic_id))
        if not t.posts_crawled:
            try:
                base_url = URL(t.category.forum.url)
                url = (base_url / ("/t/" + str(t.topic_id) + ".json"))
                resp = self.browser.get(url)
                t.topic_json = resp.content
                json_topic = json.loads(resp.content)
                n_posts = self.create_posts(t, json_topic)
                remaining_posts = json_topic["post_stream"]["stream"][n_posts:]
                while len(remaining_posts) > 0:
                    next_posts = remaining_posts[:20]
                    logging.debug(str(next_posts))
                    url = (base_url / ("/t/" + str(t.topic_id) + "/posts.json")) \
                        .with_query({"post_ids[]": tuple(next_posts), "include_suggested": "true"})
                    logging.debug("URL:"+str(url))
                    resp = self.browser.get(url)
                    json_posts = json.loads(resp.content)
                    n_posts = self.create_posts(t, json_posts)
                    remaining_posts = remaining_posts[n_posts:]
                t.posts_crawled = True
            except Exception as e:
                logging.info("****Exception in topic "+str(t.topic_id))
            self.session.commit()
            logging.info("Finished crawling topic "+str(t.topic_id))
        else:
            logging.info("Topic "+str(t.topic_id)+" has already been crawled")

    def create_posts(self, t: Topic, json_posts):
        logging.debug(json_posts)
        posts = json_posts["post_stream"]["posts"]
        for post in posts:
            if self.session.scalars(find_post_query(post["id"],t.id)).first() is None:
                p = Post(post_id=post["id"], topic_id=t.id, json=json.dumps(post))
                self.session.add(p)
        return len(posts)




