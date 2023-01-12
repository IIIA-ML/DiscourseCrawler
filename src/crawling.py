import logging
import mechanicalsoup as ms
from ratelimiter import RateLimiter
from database import Forum
from urlpath import URL
from sqlalchemy import select


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


rate_limiter = RateLimiter(max_calls=3, period=1, callback=limited)
browser = RLBrowser(rate_limiter)


def start_discourse_crawling(url: str, session):
    base_url = URL(url)
    forum = Forum(url=url)
    session.add(forum)
    session.commit()


def create_posts(t: Topic, json_posts, session):
    print(json_posts)
    posts = json_posts["post_stream"]["posts"]
    for post in posts:
        p = Post(post_id=post["id"], topic_id=t.id, json=json.dumps(post))
        session.add(p)
    return len(posts)


def crawl_topic(t: Topic, base_url, browser, session):
    print("Crawling topic ", t.topic_id)
    if not t.posts_crawled:
        url = (base_url / ("/t/" + str(t.topic_id) + ".json"))
        resp = browser.get(url)
        t.topic_json = resp.content
        json_topic = json.loads(resp.content)
        n_posts = create_posts(t, json_topic, session)
        remaining_posts = json_topic["post_stream"]["stream"][n_posts:]
        while len(remaining_posts) > 0:
            next_posts = remaining_posts[:20]
            print(next_posts)
            url = (base_url / ("/t/" + str(t.topic_id) + "/posts.json")) \
                .with_query({"post_ids[]": tuple(next_posts), "include_suggested": "true"})
            print("URL:", url)
            resp = browser.get(url)
            print(resp)
            print(resp.content)
            json_posts = json.loads(resp.content)
            n_posts = create_posts(t, json_posts, session)
            remaining_posts = remaining_posts[n_posts:]
        t.posts_crawled = True
        session.commit()


def crawl_category(c: Category, base_url, browser, session):
    print("Crawling category ", c.category_id)
    if not c.pages_crawled:
        query = select(Page) \
            .where(Page.category_id == c.id) \
            .order_by(Page.page_id.desc())
        last_page = session.execute(query).first()
        if last_page is not None:
            last_page = last_page[0]
        print(last_page)
        # print(last_page.keys())
        # i = 0
        while (last_page is None) or (last_page.more_topics_url is not None):
            # if i>3:
            #    break
            # else:
            #    i+=1
            if last_page is None:
                url = (base_url / ("/c/" + str(c.category_id) + ".json")).with_query({"page": 0})
                next_page_id = 0
            else:
                next_page_id = last_page.page_id + 1
                more_url = last_page.more_topics_url.replace("?", ".json?")
                url = (base_url / more_url)
            print(url)
            resp = browser.get(url)
            json_page = json.loads(resp.content)
            # print(json_page)
            topic_list = json_page["topic_list"]
            more_topics_url = topic_list["more_topics_url"] if "more_topics_url" in topic_list else None
            p = Page(category_id=c.id,
                     page_id=next_page_id,
                     more_topics_url=more_topics_url,
                     json=resp.content)
            session.add(p)
            this_page_topics = []
            for topic in topic_list["topics"]:
                t = Topic(topic_id=topic["id"], category_id=c.id, page_excerpt_json=json.dumps(topic))
                this_page_topics.append(t)
                session.add(t)
            session.commit()
            for t in this_page_topics:
                crawl_topic(t, base_url, browser, session)
            last_page = p


def crawl_forum(forum_id, base_url, browser, session):
    f = session.get(Forum, forum_id)
    if not f.categories_crawled:
        resp = browser.get(base_url / "categories.json")
        category_list = json.loads(resp.content)["category_list"]
        print(category_list.keys())
        categories = category_list["categories"]
        for cat in categories:
            c = Category(category_id=cat["id"], forum_id=f.id, topic_url=cat["topic_url"], json=json.dumps(cat))
            session.add(c)
        f.categories_crawled = True
        session.commit()
    for c in f.categories:
        crawl_category(c, base_url, browser, session)

        print(c.category_id)
        # q = session.execute(select(Category).where(Category.forum_id==))
        # for category in session.get(Categories):
