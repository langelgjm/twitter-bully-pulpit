import twitter
import csv
import itertools

CONSUMER_KEY = ''
CONSUMER_SECRET = ''
OAUTH_TOKEN = ''
OAUTH_TOKEN_SECRET = ''

auth = twitter.oauth.OAuth(OAUTH_TOKEN, OAUTH_TOKEN_SECRET,
                           CONSUMER_KEY, CONSUMER_SECRET)                         

t = twitter.Twitter(auth=auth)
members = t.lists.members(owner_screen_name="cspan", slug="members-of-congress", count=5000)
moc = []
for user in members['users']:
    moc.append(user['screen_name'])
    
commissioners = ["mikeofcc", "AjitPaiFcc", "MClyburnFCC", "JRosenworcel", "TomWheelerFCC"]
other = ["BarackObama", "PennyPritzker"]

def concat(*lists):
    return itertools.chain(*lists)

handles = concat(moc, commissioners, other)

f = open("twitter_handles.csv", 'w')
w = csv.writer(f)

for handle in handles:
    w.writerow([handle])

f.close()