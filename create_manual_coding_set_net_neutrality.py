from TwitterCommon import TweetDB, make_config_dict
import configparser
import csv
import random

def write_tocode_tweets(ts, path):
    '''
    Write a CSV file with the terms and their frequencies
    '''
    f = open(path, 'w')
    w = csv.writer(f, encoding='utf8')
    w.writerow(("class", "Text", "user_bio_summary", "tweet_url", "username", "real_name", "hashtags", "user_location", "user_mention", "user_mention_username", "is_retweet", "id", "id_text"))
    for t in ts:
        # Choose what is written here
        # Note that the ID MUST be written as a string because of its size
        r = ("", t.Text, t.user_bio_summary, str(t.tweet_url), t.username, t.real_name, str(t.hashtag), t.user_location, str(t.user_mention), str(t.user_mention_username), t.is_retweet, t.id, '"' + str(t.id) + '"')
        w.writerow(r)
    f.close()

def update_manual_code_tbl(mydb, tmp_rs, random_set):
    for r in tmp_rs:
        mydb.c.execute('''INSERT INTO manual_code (id, random_set) VALUES (?, ?)''', (r['id'], random_set))
        mydb.conn.commit()
    mydb.c.execute('''REINDEX index_manual_code_id''')
    mydb.conn.commit()    

def main():
    config_file = "tweets.conf"
    config = configparser.ConfigParser()
    config.read(config_file)
    myconfig = make_config_dict(config)
    
    mydb = TweetDB(myconfig['general']['db_file'])
    #mydb.c.execute('''CREATE INDEX index_manual_code_id ON manual_code (id)''')    

    print("Gathering random sample (6).")
    # Select 3000 tweets at random (1000 per coder)
    rs = mydb.sample(n=300, where="about_cc == 1", id_only=True)
    # Save ids in manual_code table
    update_manual_code_tbl(mydb, rs, 6)

    # print "Gathering samples (6)."
    # Select a total of 3000 tweets with targeted keywords to boost the proportion of putatively opposing tweets in the set
    # Note that with this we might end up with dupes...
    # Using #tcot hashtag (top conservatives on twitter)
    #tmp_rs = mydb.sample(n=750, where="id IN (SELECT tweet_id FROM hashtags WHERE hashtag=='tcot') AND about_nn == 1 AND id NOT IN (SELECT id FROM manual_code)", id_only=True)
    #update_manual_code_tbl(mydb, tmp_rs, 2)
    #rs.extend(tmp_rs)
    # mentioning "govt" (often anti-government)
    #tmp_rs = mydb.sample(n=750, where="about_nn == 1 AND Text LIKE '%govt%' AND id NOT IN (SELECT id FROM manual_code)", id_only=True)
    #update_manual_code_tbl(mydb, tmp_rs, 3)
    #rs.extend(tmp_rs)
    # control (often about government control)
    #tmp_rs = mydb.sample(n=750, where="about_nn == 1 AND Text LIKE '%control%' AND id NOT IN (SELECT id FROM manual_code)", id_only=True)
    #update_manual_code_tbl(mydb, tmp_rs, 4)
    #rs.extend(tmp_rs)
    # (often anti) reguate and regulation, but not regulatory (as in FCC regulatory proposal/action/plan)
    #tmp_rs = mydb.sample(n=750, where="about_nn == 1 AND Text NOT LIKE '%regulato%' AND Text LIKE '%regulat%' AND id NOT IN (SELECT id FROM manual_code)", id_only=True)
    #update_manual_code_tbl(mydb, tmp_rs, 5)
    #rs.extend(tmp_rs)
    
    print("Creating coding sets.")
        
    # This gives us a total of 6000.
    # Randomly assign 2000 to a given coder.
    # Note that using set logic eliminates duplicates between the three, so the third coder will have slightly < 2000
    tocode_id = {}
    tocode_id['gabe'] = rs
    #tocode_id['colin'] = random.sample(rs, 2000)
    #tocode_id['cory'] = random.sample(list(set(rs) - set(tocode_id['colin'])), 2000)
    #tocode_id['gabe'] = list(set(rs) - set(tocode_id['colin']) - set(tocode_id['cory']))

    # overlap_id = {}
    # # Then, randomly assign 200 from each other coder's set to the third coder
    # for k in tocode_id.keys():
    #     print k
    #     for j in list(set(tocode_id.keys()) - set([k])):
    #         print "----" + str(j)
    #         samp = random.sample(tocode_id[j], 200)
    #         print len(set(tocode_id[k]).intersection(set(samp)))
    #         try:
    #             overlap_id[k].extend(samp)
    #         except KeyError:
    #             overlap_id[k] = samp
    #
    # for k in tocode_id.keys():
    #     tocode_id[k].extend(overlap_id[k])
            
    # tocode = {'gabe': [], 'colin': [], 'cory': []}
    tocode = {'gabe': []}
    for k in list(tocode_id.keys()):
        for tid in tocode_id[k]:
            t = mydb.search(tid['id'])[0]
            tocode[k].append(t)
        write_tocode_tweets(tocode[k], "data/tocode_" + k + ".csv")

    # This gives a total of 2400 per code, of which 2000 are unique
    mydb.close()
    print("Done.")

if __name__ == "__main__":
    main()