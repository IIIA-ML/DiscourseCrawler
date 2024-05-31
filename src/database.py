from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, UniqueConstraint, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Forum(Base):
    __tablename__ = "forum"
    id = Column(Integer, primary_key=True)
    url = Column(String)
    categories_crawled = Column(Boolean, unique=False, default=False)
    categories = relationship("Category", back_populates="forum", cascade="all, delete-orphan")
    users = relationship("User", back_populates="forum", cascade="all, delete-orphan")

class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    forum_id = Column(Integer, ForeignKey('forum.id'))
    json = Column(Text)
    forum = relationship("Forum", back_populates="users")


class Category(Base):
    __tablename__ = "category"
    id = Column(Integer, primary_key=True)
    category_id = Column(Integer)
    forum_id = Column(Integer, ForeignKey('forum.id'))
    topic_url = Column(String)
    json = Column(Text)
    pages_crawled = Column(Boolean, unique=False, default=False)
    forum = relationship("Forum", back_populates="categories")
    pages = relationship("Page", back_populates="category", cascade="all, delete-orphan")
    topics = relationship("Topic", back_populates="category", cascade="all, delete-orphan")
    __table_args__ = (UniqueConstraint('category_id', 'forum_id', name='alternate_key_cat_forum'),
                      )


class Page(Base):
    __tablename__ = "page"
    id = Column(Integer, primary_key=True)
    page_id = Column(Integer)
    category_id = Column(Integer, ForeignKey('category.id'))
    more_topics_url = Column(String)
    json = Column(Text)
    category = relationship("Category", back_populates="pages")
    __table_args__ = (UniqueConstraint('category_id', 'page_id', name='alternate_key_page_cat'),)


# %%

class Topic(Base):
    __tablename__ = "topic"
    id = Column(Integer, primary_key=True)
    topic_id = Column(Integer)
    category_id = Column(Integer, ForeignKey('category.id'))
    page_excerpt_json = Column(Text)
    topic_json = Column(Text)
    category = relationship("Category", back_populates="topics")
    posts_crawled = Column(Boolean, unique=False, default=False)
    posts = relationship("Post", back_populates="topic", cascade="all, delete-orphan")
    __table_args__ = (UniqueConstraint('category_id', 'topic_id', name='alternate_key_topic_cat'),)


class Post(Base):
    __tablename__ = "post"
    id = Column(Integer, primary_key=True)
    post_id = Column(Integer)
    topic_id = Column(Integer, ForeignKey('topic.id'))
    json = Column(Text)
    topic = relationship("Topic", back_populates="posts")
    __table_args__ = (UniqueConstraint('topic_id', 'post_id', name='alternate_key_post_topic'),)



def create_database(engine):
    Base.metadata.create_all(engine)
