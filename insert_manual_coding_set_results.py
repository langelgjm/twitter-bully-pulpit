from TwitterCommon import TweetDB, make_config_dict
import configparser
import csv
import pandas

def main():
    config_file = "tweets.conf"
    config = configparser.ConfigParser()
    config.read(config_file)
    myconfig = make_config_dict(config)
    
    mydb = TweetDB(myconfig['general']['db_file'])    
    
    mycodes = {}

    for k in myconfig['general'].keys():
        if k.startswith("training_file"):
            try:
                f = open(myconfig['general'][k], 'r')
            except FileNotFoundError:
                continue
            r = csv.reader(f)
            # Skip the header row
            next(r)
            for row in r:
                tweet_class = row[0]
                # Remove first and last chars (quotes), and cast to int
                tweet_id = int(row[12][1:-1])
                if not str(tweet_id) in mycodes.keys():
                    mycodes[str(tweet_id)] = tweet_class
                # Always take a code over NA
                elif mycodes[str(tweet_id)] == 'na':
                    mycodes[str(tweet_id)] = tweet_class
                # Here is where we resolve discrepant coding by deferring to master coder
                elif k == "training_file1":
                    mycodes[str(tweet_id)] = tweet_class

    print ("Tabulating codes.")
    df = pandas.DataFrame.from_dict(mycodes, orient='index')
    df.columns = ["class"]
    for k in df.groupby("class").groups.keys():
        print(len(df.groupby("class").groups[k]))   

    print("Inserting manually coded tweets.")
    for tweet_id in mycodes.keys():
        mydb.c.execute('''UPDATE manual_code SET class = ? WHERE id = ?''', (mycodes[tweet_id], int(tweet_id)))
    mydb.conn.commit()
    mydb.close()
    print("Done with all files.")
    
if __name__ == "__main__":
    main()