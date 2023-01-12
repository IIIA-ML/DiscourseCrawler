# DiscourseCrawler

Crawls a discourse instance

## Usage example

Requires a working Python installed on your machine with the capability to create virtual environments.

1. Clone the repo
2. source bin/init-local.sh
3. bin/discourse_crawler -d db/cientopolis.org.db -u https://forum.cientopolis.org -r

## Time estimates

It takes about one hour to crawl the inaturalist.org forum, which has over 160K posts.

## Already crawled forums

The databases for the forums which have already being crawled can be found at

https://saco.csic.es/index.php/s/sAeyw6mCm4TPz4M?path=%2Fdiscourse_forums_dbs

The databases from crawling are *raw* in the sense that they only contain the information required for crawling and the json excerpts resulting from the crawling. 
The idea is that these databases are now transformed into a properly structured database before they are mined.
