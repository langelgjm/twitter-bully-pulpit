from TwitterCommon import TweetCSV, Tweet, TweetDB, make_config_dict
import ConfigParser
from sqlite3 import IntegrityError

def main():
    config_file = "tweets.conf"
    config = ConfigParser.ConfigParser()
    config.read(config_file)
    myconfig = make_config_dict(config)
    
    mydb = TweetDB(myconfig['general']['db_file'])
    
    for k in myconfig['general'].keys():
        if k.startswith("csv_file"):
            print "Inserting tweets from " + str(k)
            mycsv = TweetCSV(myconfig['general'][k])    
            try:
                while mycsv:
                    mytweet = Tweet()
                    mytweet.from_csv(mycsv.next())
                    try:
                        mydb.insert(mytweet)
                    except IntegrityError:
                        continue
            except StopIteration:
                print "Done with " + str(k)
            except IndexError as e:
                print e
                print mytweet
            finally:
                mycsv.close()
    mydb.close()
    print "Done with all files."
    
if __name__ == "__main__":
    main()