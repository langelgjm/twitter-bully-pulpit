from TwitterCommon import TweetDB, make_config_dict
import configparser
import csv

def write_tocode_tweets(ts, path):
    '''
    Write a CSV file with the terms and their frequencies
    '''
    f = open(path, 'w')
    w = csv.writer(f)
    w.writerow(("class", "Text", "user_bio_summary", "tweet_url", "username", "real_name", "hashtags", "user_location", "user_mention", "user_mention_username", "is_retweet", "id", "id_text"))
    for t in ts:
        # Choose what is written here
        # Note that the ID MUST be written as a string because of its size
        r = ("", t.Text, t.user_bio_summary, str(t.tweet_url), t.username, t.real_name, str(t.hashtag), t.user_location, str(t.user_mention), str(t.user_mention_username), t.is_retweet, t.id, '"' + str(t.id) + '"')
        w.writerow(r)
    f.close()

def main():
    config_file = "tweets.conf"
    config = configparser.ConfigParser()
    config.read(config_file)
    myconfig = make_config_dict(config)

    mydb = TweetDB(myconfig['general']['db_file'])

    rs = mydb.c.execute('''SELECT id FROM manual_code WHERE random_set=6''').fetchall()

    print("Creating coding sets.")
    tocode_id = {}
    tocode_id['gabe'] = rs
    tocode = {'gabe': []}
    for k in list(tocode_id.keys()):
        for tid in tocode_id[k]:
            t = mydb.search(tid['id'])[0]
            tocode[k].append(t)
        write_tocode_tweets(tocode[k], "data/tocode_" + k + ".csv")

    mydb.close()
    print("Done.")

if __name__ == "__main__":
    main()