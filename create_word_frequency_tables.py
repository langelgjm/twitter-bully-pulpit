from TwitterCommon import TweetDB, make_config_dict
import ConfigParser
from sklearn.feature_extraction.text import CountVectorizer
from nltk.stem import PorterStemmer, LancasterStemmer, WordNetLemmatizer
import unicodecsv
from string import maketrans

def write_tf(vocab, tf, path):
    '''
    Write a CSV file with the terms and their frequencies
    '''
    f = open(path, 'w')
    w = unicodecsv.writer(f, encoding='utf8')
    for i, t in enumerate(vocab):
        w.writerow((t, tf[i]))
    f.close()

def get_tf(db, tweet_ids, n=25, stemmer_choice="porter"):
    '''
    Return list of n most frequent terms, and another list of their frequencies.
    '''

    if stemmer_choice == "lancaster":
        stemmer = LancasterStemmer()
    elif stemmer_choice == "wordnet":
        stemmer = WordNetLemmatizer()
        # WordNetLemmatizer expects a different format for POS tags
        pos_translator = maketrans("N^SZVAR", "nnnnvar")
    else:
        stemmer = PorterStemmer()
        
    cv = CountVectorizer(stop_words = "english", strip_accents = "unicode", analyzer = "word", ngram_range=(1, 1), max_features=n)
    
    stemmed_tweets = []
    
    for r in tweet_ids:
        # Get tokens and parts of speech from database
        ps = db.c.execute('''SELECT token, pos FROM pos WHERE tweet_id == (?)''', (r['id'], )).fetchall()
        tokens = []
        parts_of_speech = []
        for p in ps:
            # We exclude many uninteresting parts of speech.
            #if not p[1] in ('!', '#', '$', '&', ',', 'D', 'E', 'G', 'L', 'O', 'P', 'U', '~'):
            if p[1] in ('N', '^', 'S', 'Z', 'V', 'A', 'R', '@', 'L', 'M'):
                tokens.append(p[0])
                parts_of_speech.append(p[1])
        stems = []
        for i, t in enumerate(tokens):
            if stemmer_choice != "wordnet":
                stems.append(stemmer.stem(t))
            else:
                new_pos = parts_of_speech[i].translate(pos_translator)
                if new_pos in ('n', 'v', 'a', 'r'):
                    stems.append(stemmer.lemmatize(t, pos = new_pos))
                else:
                    stems.append(stemmer.lemmatize(t))
        stemmed_tweet = u" ".join(stems)
        stemmed_tweets.append(stemmed_tweet)

    mat = cv.fit_transform(stemmed_tweets)
    vocab = cv.get_feature_names()
    # Column sums represent feature frequencies
    tf = mat.sum(0).tolist()[0]
    return vocab, tf

def main():
    config_file = "tweets.conf"
    config = ConfigParser.ConfigParser()
    config.read(config_file)
    myconfig = make_config_dict(config)
    
    mydb = TweetDB(myconfig['general']['db_file'])
    
    #mydb.create_tables()
    # Build the parts of speech table (will take a long time)
    #print "Building and indexing parts of speech table..."
    #mydb.parts_of_speech(myconfig['general']['ark_tweet_nlp_cmd'])
    
    print "Creating word frequency tables."
    
    stemmer_choice = "wordnet"

    for clump in ("nn", "cc"):
        path = "data/" + clump + "_" + stemmer_choice + "_pre_vocab.csv"
        ids = mydb.c.execute('''SELECT id FROM tweets WHERE about_''' + clump + ''' == 1 AND posted_time_iso8601 < (?)''', ("2014-11-10T15:00:00", )).fetchall()
        vocab, tf = get_tf(mydb, ids, n=25, stemmer_choice=stemmer_choice)
        write_tf(vocab, tf, path)
        path = "data/" + clump + "_" + stemmer_choice + "_post_vocab.csv"
        ids = mydb.c.execute('''SELECT id FROM tweets WHERE about_''' + clump + ''' == 1 AND posted_time_iso8601 >= (?)''', ("2014-11-10T15:00:00", )).fetchall()
        vocab, tf = get_tf(mydb, ids, n=25, stemmer_choice=stemmer_choice)
        write_tf(vocab, tf, path)
    
    print "Done."

if __name__ == "__main__":
    main()