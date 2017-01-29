from TwitterCommon import TweetDB, make_config_dict
import configparser

def main():
    config_file = "tweets.conf"
    config = configparser.ConfigParser()
    config.read(config_file)
    myconfig = make_config_dict(config)
    
    mydb = TweetDB(myconfig['general']['db_file'])   
    mydb.parts_of_speech("user_bio_summary", myconfig['general']['ark_tweet_nlp_cmd'])

if __name__ == "__main__":
    main()