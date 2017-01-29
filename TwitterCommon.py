import sqlite3
import random
from ark import CMUTweetTagger
from urllib.parse import urlparse
from multiprocessing import Pool
from math import ceil
from nltk.stem import WordNetLemmatizer, porter
import numpy as np
# This needs to be fixed for python 3
import csv

def chunks(l, n):
    '''
    Generator to yield n-size chunks of an iterable l
    '''
    for i in range(0, len(l), n):
        yield l[i:i+n]

def chunks_np(l, n):
    '''
    Generator to yield n-size chunks of an iterable l
    '''
    for i in range(0, np.shape(l)[0], n):
        yield l[i:i+n]


class TweetCSV(object):
    '''
    CSV export file containing raw tweet data
    '''
    def __init__(self, csv_file):
        self.f = open(csv_file, 'r')
        self.file = self.f.name        
        self.reader = csv.reader(self.f, encoding='utf-8-sig')
        # Create list of future keys from header row column names:
        self.column_names = []
        for c in self.reader.next():
            s = c
            s = s.replace(" ", "")
            s = s.replace(":", "")
            s = s.replace("[M]", "")
            self.column_names.append(s)
    def __iter__(self):
        return self.reader.__iter__()
    def next(self):
        d = {}
        for i, c in enumerate(self.reader.next()):
            d[self.column_names[i]] = c
        return d
    def close(self):
        self.f.close()

class Tweet(object):
    '''
    Tweets are created either from CSV file input or from the results of an SQL query.
    Call the appropiate method (from_csv or from_db) on the data to create them.
    '''
    #def __init__(self):
    def __len__(self):
        '''
        Return character length of tweet text. If no tweet data, returns None.
        '''
        try:
            return len(self.Text)
        except AttributeError:
            return None
    def __repr__(self):
        return repr(self.__dict__)
    def __nonzero__(self):
        return True
    def keys(self):
        return self.__dict__.keys()
    def from_db(self, tweet_data, hashtag_data, url_data, mention_data, pos=None):
        '''
        Pass this SQLite rows from SELECT queries on tweets, hashtags, url, mentions, and pos
        '''
        for k in tweet_data.keys():
            self.__setattr__(k, tweet_data[k])
        self.hashtag = []
        for r in hashtag_data:
            (h, ) = r
            self.hashtag.append(h)
        self.tweet_url = []
        for r in url_data:
            (u, ) = r
            self.tweet_url.append(u)
        self.user_mention = []
        self.user_mention_username = []
        for r in mention_data:
            # Note that here we'll get a list of tuples
            (real_name, user_name) = r
            self.user_mention.append(real_name)
            self.user_mention_username.append(user_name)
        self.token = []
        self.pos = []
        self.conf = []
        self.bio_token = []
        self.bio_pos = []
        self.bio_conf = []
        if pos:
            for r in pos:
                # Note that here we'll get a list of 4-tuples
                (token, pos, conf, col) = r
                if col == "Text":
                    self.token.append(token)
                    self.pos.append(pos)
                    self.conf.append(conf)
                elif col == "user_bio_summary":
                    self.bio_token.append(token)
                    self.bio_pos.append(pos)
                    self.bio_conf.append(conf)
        self.source = "db"
    def get_pos(self):
        '''
        Retrieve and store parts of speech for tweets in the database.
        Don't use this method.
        '''
        if self.source == "db":
            rs = self.c.execute('''SELECT token, pos, conf FROM pos WHERE tweet_id == (?)''', (self.id, )).fetchall()
            self.pos_tokens =  []
            self.pos = []
            self.pos_conf = []
            for r in rs:
                self.pos_tokens.append(r['token'])
                self.pos.append(r['pos'])
                self.pos_conf.append(r['conf'])
        else:
            print("Cannot get parts of speech from a CSV file.")
    def from_csv(self, csv_data):
        '''
        Pass this a row of the CSV file input
        '''
        # exclude special keys (i.e., those that need to be formatted as lists)
        list_keys = ("hashtag", "tweet_url")
        mention_keys = ("user_mention", "user_mention_username")
        ks = list(set(csv_data.keys()) - set(list_keys) - set(mention_keys))
        for k in ks:
            self.__setattr__(k, csv_data[k])
        for k in list(set(list_keys).union(set(mention_keys))):
            # All of these special keys string lists separated by a semicolon/space combo
            l = csv_data[k].split("; ")
            self.__setattr__(k, l)
        if len(self.user_mention) != len(self.user_mention_username):
            # If these are not the same, use just the usernames
            self.user_mention = list(self.user_mention_username)
        self.id = self.id.replace("tag:search.twitter.com,2005:", "")
        self.posted_time = self.posted_time.replace("/", "-")
        self.posted_date, self.posted_timeonly = self.posted_time.split()
        if not self.is_retweet:
            self.is_retweet = 0
        else:
            self.is_retweet = len(self.is_retweet.split())
        self.source = "csv"
    def store_pos(self, pos):
        self.pos = pos
        parsedText = []    
        for w in self.pos:
            if not w[1] in ("U", ",", "~", "@"):
                parsedText.append(w[0].decode('utf8'))
        s = u" "
        parsedText = s.join(parsedText)
        self.parsedText = parsedText
            
class TweetDB(object):
    def __init__(self, db_file):
        self.db_file = db_file
        self.conn = sqlite3.connect(db_file)
        self.conn.row_factory = sqlite3.Row
        self.c = self.conn.cursor()
        # Check if we need to create tables:
        r = self.c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tweets'").fetchone()
        if r is None:
            self.create_tables()
    def __len__(self):
        try:
            (n, ) = self.c.execute('''SELECT COUNT(*) FROM tweets''').fetchone()
        except sqlite3.OperationalError:
            n = 0
        return n
    def __repr__(self):
        s = "<SQLite database of " + str(len(self)) + " tweets stored in '" + self.db_file + "'>"
        return s
    def __nonzero__(self):
        return True
    def create_tables(self):
        '''
        Used once to create the empty tables.
        Note that after inserting all tweets, one should run the following:
        
        UPDATE tweets SET about_nn = 1 WHERE Text LIKE "%net neutrality%" OR Text LIKE "%netneutrality%";
        UPDATE tweets SET about_nn = 0 WHERE about_nn IS NULL;
        
        UPDATE tweets SET about_cc = 1 WHERE Text LIKE "%climate change%" OR Text LIKE "%climatechange%";
        UPDATE tweets SET about_cc = 0 WHERE about_cc IS NULL;
        
        UPDATE tweets SET about_nn = 1 WHERE id in (SELECT tweet_id FROM hashtags WHERE hashtag LIKE "netneutrality");
        UPDATE tweets SET about_cc = 1 WHERE id in (SELECT tweet_id FROM hashtags WHERE hashtag LIKE "climatechange");
        
        # Use this to fix dates and times by converting to ISO 8601 format and storing result in additional colmuns
        UPDATE tweets SET posted_date_iso8601 = CASE WHEN length(ltrim(substr(posted_date,-5,-2),"-")) < 2 THEN substr(posted_date,-4,4) || "-" || substr(posted_date,1,3) || "0" || ltrim(substr(posted_date,-5,-2),"-") ELSE substr(posted_date,-4,4) || "-" || substr(posted_date,1,3) || substr(posted_date,-5,-2) END;
        UPDATE tweets SET posted_time_iso8601 = posted_date_iso8601 || "T" || posted_timeonly || "Z";
        
        # To see hourly distribution for a given day, e.g.:
        SELECT substr(posted_timeonly,1,2), count(*) FROM tweets WHERE posted_date_iso8601 == "2014-11-10" GROUP BY substr(posted_timeonly,1,2);
        '''
        self.c.execute('''CREATE TABLE IF NOT EXISTS tweets (Title TEXT,
                                            Text TEXT,
                                            UnitId TEXT,
                                            country_code TEXT,
                                            favorites_count INTEGER,
                                            followers_count INTEGER,
                                            friends_count INTEGER,
                                            hashtag TEXT,
                                            id INTEGER PRIMARY KEY,
                                            is_retweet INTEGER,
                                            link TEXT,
                                            location_coord_type TEXT,
                                            location_coords TEXT,
                                            location_displayname TEXT,
                                            location_type TEXT,
                                            media_display_url TEXT,
                                            media_type TEXT,
                                            media_url TEXT,
                                            posted_time TEXT,
                                            posted_date TEXT,
                                            posted_timeonly TEXT,
                                            real_name TEXT,
                                            source TEXT,
                                            statuses_count INTEGER,
                                            tweet_url TEXT,
                                            user_bio_summary TEXT,
                                            user_location TEXT,
                                            user_mention TEXT,
                                            user_mention_username TEXT,
                                            user_twitter_page TEXT,
                                            username TEXT,
                                            about_nn INTEGER,
                                            about_cc INTEGER
                                            )''')
        self.c.execute('''CREATE TABLE IF NOT EXISTS hashtags (id INTEGER PRIMARY KEY,
                                            tweet_id INTEGER,
                                            hashtag TEXT,
                                            FOREIGN KEY(tweet_id) REFERENCES tweets(id)
                                            )''')
        self.c.execute('''CREATE TABLE IF NOT EXISTS urls (id INTEGER PRIMARY KEY,
                                            tweet_url TEXT,
                                            tweet_id INTEGER,
                                            FOREIGN KEY(tweet_id) REFERENCES tweets(id)
                                            )''')
        self.c.execute('''CREATE TABLE IF NOT EXISTS mentions (id INTEGER PRIMARY KEY,
                                            tweet_id INTEGER,
                                            user_mention TEXT,
                                            user_mention_username TEXT,
                                            FOREIGN KEY(tweet_id) REFERENCES tweets(id)
                                            )''')
        self.c.execute('''CREATE TABLE IF NOT EXISTS pos (id INTEGER PRIMARY KEY,
                                            tweet_id INTEGER,
                                            token TEXT,
                                            pos TEXT,
                                            conf REAL,
                                            FOREIGN KEY(tweet_id) REFERENCES tweets(id)
                                            )''')
        self.c.execute('''CREATE TABLE IF NOT EXISTS manual_code (id INTEGER PRIMARY KEY, random_set INTEGER)''')         
        self.c.execute('''CREATE INDEX IF NOT EXISTS index_manual_code_id ON manual_code (id)''')                                   
        self.conn.commit()
    def insert(self, tweet):
        self.c.execute('INSERT INTO tweets (id) VALUES (?)', (tweet.id,))
        pk = self.c.lastrowid
        # define keys that can be inserted without special handling
        ks = list(set(tweet.__dict__.keys()) - set(("hashtag", "tweet_url", "user_mention", "user_mention_username")))
        for k in ks:
            # Now update the new record with the remaining values
            self.c.execute('UPDATE tweets SET ' + k + '=? WHERE ROWID=?', (tweet.__dict__[k], pk))
        while tweet.hashtag:
            self.c.execute('INSERT INTO hashtags (tweet_id, hashtag) VALUES (?, ?)', (pk, tweet.hashtag.pop()))
        while tweet.tweet_url:
            self.c.execute('INSERT INTO urls (tweet_id, tweet_url) VALUES (?, ?)', (pk, tweet.tweet_url.pop()))
        while tweet.user_mention:
            self.c.execute('INSERT INTO mentions (tweet_id, user_mention, user_mention_username) VALUES (?, ?, ?)', (pk, tweet.user_mention.pop(), tweet.user_mention_username.pop()))
        self.conn.commit()        
        #print "Inserted " + tweet.id + " into database."
        return pk
    def parts_of_speech_subprocess(self, chunk):
        '''
        The subprocess called by multiprocessor map to tag parts of speech
        '''
        id_list, text_list = zip(*chunk)
        pos_list = CMUTweetTagger.runtagger_parse(text_list, run_tagger_cmd=self.run_tagger_cmd)
        return list(zip(id_list, pos_list))
    def parts_of_speech(self, col, cmd):
        '''
        Compute parts of speech for each tweet Text in the database and store in the 'pos' table.
        This will take a long time.
        'cmd' argument is specified in the configuration file, and might be passed as myconfig['general']['ark_tweet_nlp_cmd']
        Builds an index at the end.
        '''
        self.run_tagger_cmd = cmd
        rs = self.c.execute("SELECT id, " + col  + " FROM tweets WHERE " + col + " != ''").fetchall()
        # Split result set into 4 roughly equally sized chunks
        chunksize = int(ceil(len(rs) / 4))
        id_list = [r["id"] for r in rs]
        text_list = [r[col] for r in rs]
        map_onto = []
        for chunk in chunks(list(zip(id_list, text_list)), chunksize):
            map_onto.append(chunk)
        # Send to subprocess pool
        p = Pool(processes=4)
        map_rs = p.map(self.parts_of_speech_subprocess, map_onto, 1)
        # recombine the four separate lists into one big list for insertion
        pos_list = []
        for r in map_rs:
            pos_list.extend(r)
        # Process list for insertion
        for tweet_id, pos in pos_list:
            # iterate through list of tuples (each tuple being a token)
            for t in pos:
                self.c.execute('''INSERT INTO pos (tweet_id, token, pos, conf, col) VALUES (?, ?, ?, ?, ?)''', (tweet_id, t[0].decode('utf8'), t[1].decode('utf8'), t[2], col))
        self.conn.commit()
        #self.c.execute('''CREATE INDEX index_tweet_id ON pos (tweet_id)''')
        #self.c.execute('''CREATE INDEX index_pos_tweet_id ON pos (tweet_id)''')        
    def search(self, search_term):
        '''
        Return a list of Tweet objects matching search_term. If none found, returns an empty list
        Needs to be rewritten to handle all possible search queries
        '''
        #isbn = self.fmt_isbn(search_term)
        #if isbn["isbn_type"] != "invalid":
        r = self.c.execute('''SELECT * FROM tweets WHERE id=?''', (search_term,))
        #elif search_term.isdigit():
            # Here we assume that it is simply an invalid ISBN
            #return False
        #else:
            # Any other input is treated as a potential title
            #r = self.c.execute('''SELECT * FROM library WHERE title LIKE ?''', ('%' + search_term + '%',))
        tweet_data = r.fetchall()
        tweets = []
        for t in tweet_data:
            hashtag_data = self.c.execute('''SELECT hashtag FROM hashtags WHERE tweet_id=?''', (t["id"],)).fetchall()
            url_data = self.c.execute('''SELECT tweet_url FROM urls WHERE tweet_id=?''', (t["id"],)).fetchall()
            mention_data = self.c.execute('''SELECT user_mention, user_mention_username FROM mentions WHERE tweet_id=?''', (t["id"],)).fetchall()
            tweet = Tweet()            
            tweet.from_db(t, hashtag_data, url_data, mention_data)
            # Needs to be fixed
            #tweet.get_pos()
            tweets.append(tweet)
            #print "Found " + str(tweet.id) + " in database."
        return tweets
    def search_id(self, tweet_id):
        '''
        Return a single tweet from the database matching tweet_id. If none found, returns None.
        '''
        tweet_data = self.c.execute('''SELECT * FROM tweets WHERE id=?''', (tweet_id,)).fetchone()
        if not tweet_data is None:
            hashtag_data = self.c.execute('''SELECT hashtag FROM hashtags WHERE tweet_id=?''', (tweet_data["id"],)).fetchall()
            url_data = self.c.execute('''SELECT tweet_url FROM urls WHERE tweet_id=?''', (tweet_data["id"],)).fetchall()
            mention_data = self.c.execute('''SELECT user_mention, user_mention_username FROM mentions WHERE tweet_id=?''', (tweet_data["id"],)).fetchall()
            pos_data = self.c.execute('''SELECT token, pos, conf, col FROM pos WHERE tweet_id=?''', (tweet_data["id"],)).fetchall()        
            tweet = Tweet()            
            tweet.from_db(tweet_data, hashtag_data, url_data, mention_data, pos_data)
            return tweet    
        else:
            return None
    def sample(self, n, where=None, id_only=False):
        '''
        Return a random sample of n tweets. Optional where clause subsetting.
        '''
        if where is None:
            rs = self.c.execute('''SELECT id FROM tweets''').fetchall()
        else:
            rs = self.c.execute('''SELECT id FROM tweets WHERE ''' + where).fetchall()            
        ids = random.sample(rs, n)
        if not id_only:
            s = []
            for i in ids:
                (tweet_id, ) = i
                s.extend(self.search(tweet_id))
            return s
        else:
            return ids
    def close(self):
        '''
        Only call when done using database.
        '''
        self.conn.close()

class Document(object):
    def __init__(self, tweet):
        self.tweet = tweet
        self.features = []
        self.feature_list = []
    def addText(self, stem=False):
        for i, pos in enumerate(self.tweet.pos):
            if pos in ('N', '^', 'S', 'Z', 'V', 'A', 'R', '@', 'L', 'M'):
                if stem==False:
                    self.features.append(self.tweet.token[i])  
                else:
                    stemmer = porter.PorterStemmer()
                    self.features.append(stemmer.stem(self.tweet.token[i]))
        self.feature_list.append("Text")
    def addBio(self, stem=False):
        for i, pos in enumerate(self.tweet.bio_pos):
            if pos in ('N', '^', 'S', 'Z', 'V', 'A', 'R', '@', 'L', 'M'):
                if stem==False:                
                    self.features.append(self.tweet.bio_token[i])  
                else:
                    stemmer = porter.PorterStemmer()
                    self.features.append(stemmer.stem(self.tweet.bio_token[i]))
        self.feature_list.append("Text")
    def addHashtags(self):
        for hashtag in self.tweet.hashtag:
            self.features.append(hashtag)
        self.feature_list.append("Hashtags")
    def addMentions(self):
        for username in self.tweet.user_mention_username:
            self.features.append(username)
        self.feature_list.append("Mentions")        
    def addUsername(self):
        self.features.append(self.tweet.username)
        self.feature_list.append("Username")
    def addBaseURLs(self):
        for url in self.tweet.tweet_url:
            parsed_url = urlparse(url)
            self.features.append(parsed_url.netloc)
        self.feature_list.append("BaseURL")
    def stem(self):
        #wnl = WordNetLemmatizer()
        stemmer = porter.PorterStemmer()
    def toString(self):
        '''
        Call after adding all features to create a string for CountVectorizer
        '''
        return " ".join(self.features)

def make_config_dict(cp):
    '''
    Return a nested dict of sections/options by iterating through a ConfigParser instance.
    '''
    d = {}
    for s in cp.sections():
        e = {}
        for o in cp.options(s):
            e[o] = cp.get(s,o)
        d[s] = e
    return d