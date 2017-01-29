library(ggplot2)
library(scales)
library(sqldf)

db <- dbConnect(SQLite(), dbname="data/tweets.sqlite")
res <- dbSendQuery(db, "SELECT posted_date_iso8601 AS datestr, class, count(*) AS count FROM tweets WHERE about_nn == 1 GROUP BY posted_date_iso8601, class")
nn_dates <- fetch(res, n = -1)
nn_dates$date <- as.Date(nn_dates$datestr, "%Y-%m-%d")
# drop datestr
nn_dates <- nn_dates[,2:4]
date_totals <- aggregate(nn_dates$count, by=list(nn_dates$date), FUN=sum)
colnames(date_totals) <- c("date", "count")
date_totals$class = "t"
# Let's provide an indicator of volume, but transformed and scaled from 0 to 1 so it can be plotted along with the proportions
#date_totals$transformed <- scale(sqrt(date_totals$count), center=FALSE, scale=sqrt(max(date_totals$count)))
date_totals$transformed <- scale(date_totals$count, center=FALSE, scale=max(date_totals$count))
ggplot(nn_dates, aes(x=date, y=count, fill=class)) + 
  geom_bar(position="fill", stat="identity") + scale_fill_manual(values=c("gray", "#fc8d62", "#8da0cb", "#000000"), labels=c("NA", "Oppose", "Support", "Scaled Volume")) + 
  geom_line(data=date_totals,  aes(x=date, y=transformed, fill="Scaled Volume")) +
  scale_x_date(labels=date_format("%b %d"), breaks=date_breaks("day"),limits = as.Date(c('2014-11-03','2014-11-17'))) +
  labs(x = "Date", y = "Proportion", fill="") + 
  theme_classic() + 
  theme(legend.position="bottom", axis.text.x=element_text(angle=90))
ggsave(filename="nn_dates.pdf", width=9, height=6)

res <- dbSendQuery(db, "SELECT substr(posted_time_iso8601,1,13) AS timestr, class, count(*) AS count FROM tweets WHERE about_nn == 1 AND posted_date_iso8601 IN ('2014-11-10', '2014-11-11') GROUP BY substr(posted_time_iso8601,1,13), class")
nn_day <- fetch(res, n = -1)
nn_day$time <- as.POSIXct(nn_day$timestr, format = "%Y-%m-%dT%H", tz="GMT")
# Lazy fix so that bars are plotted in a better way (add half an hour to each time)
nn_day$time = nn_day$time + 1800
# drop datestr
nn_day <- nn_day[,2:4]
time_totals <- aggregate(nn_day$count, by=list(nn_day$time), FUN=sum)
colnames(time_totals) <- c("time", "count")
time_totals$class = "t"
# Let's provide an indicator of volume, but transformed and scaled from 0 to 1 so it can be plotted along with the proportions
#time_totals$transformed <- scale(sqrt(time_totals$count), center=FALSE, scale=sqrt(max(time_totals$count)))
time_totals$transformed <- scale(time_totals$count, center=FALSE, scale=max(time_totals$count))
ggplot(nn_day, aes(x=time, y=count, fill=class)) + 
  geom_bar(position="fill", stat="identity") + scale_fill_manual(values=c("gray", "#fc8d62", "#8da0cb", "#000000"), labels=c("NA", "Oppose", "Support", "Scaled Volume")) + 
  geom_line(data=time_totals,  aes(x=time, y=transformed, fill="Scaled Volume")) +
  scale_x_datetime(labels=date_format("%b %d %Hh GMT"), breaks=date_breaks("hour"), limits = as.POSIXct(c('2014-11-10 08:00:00','2014-11-11 06:00'), tz="GMT")) +
  labs(x = "Time", y = "Proportion", fill="") + 
  theme_classic() + 
  theme(legend.position="bottom", axis.text.x=element_text(angle=90)) + 
  geom_vline(xintercept = as.numeric(as.POSIXct("2014-11-10 14:20:28", tz="GMT")), linetype="longdash", color = "white") + 
  annotate("text", x = as.POSIXct("2014-11-10 14:20:28", tz="GMT") - 2400, y = 0.75, label = "@WhiteHouse", angle=90, color = "white") + 
  geom_vline(xintercept = as.numeric(as.POSIXct("2014-11-10 15:43:19", tz="GMT")), linetype="longdash", color = "white") + 
  annotate("text", x = as.POSIXct("2014-11-10 15:43:19", tz="GMT") - 1200, y = 0.25, label = "@SenTedCruz", angle=90, color = "white") + 
  geom_vline(xintercept = as.numeric(as.POSIXct("2014-11-10 22:43:17", tz="GMT")), linetype="longdash", color = "white") + 
  annotate("text", x = as.POSIXct("2014-11-10 22:43:17", tz="GMT") - 1200, y = 0.3, label = "@Oatmeal", angle=90, color = "white")
ggsave(filename="nn_day.pdf", width=9, height=6)

res <- dbSendQuery(db, "SELECT mentions.user_mention_username as handle, mentions.user_mention as name, class, count(*) as count FROM tweets INNER JOIN mentions ON tweets.id = mentions.tweet_id WHERE about_nn == 1 AND mentions.user_mention_username IS NOT NULL AND mentions.user_mention_username IN (SELECT username FROM important_handles) GROUP BY mentions.user_mention_username, class")
govt <- fetch(res, n = -1)
govt_totals <- aggregate(govt$count, by=list(govt$handle), FUN=sum)
colnames(govt_totals) <- c("handle", "count")
govt_totals <- merge(govt, govt_totals, by="handle", suffixes = c(".class", ".total"))
impt_govt <- govt_totals[govt_totals$count.total >= 50,]
# Could use square root here again, or log
impt_govt$transformed <- log(impt_govt$count.total)
impt_govt$proportion <- impt_govt$count.class / impt_govt$count.total
impt_govt_support <- impt_govt[impt_govt$class=="s",]
impt_govt_support <- impt_govt_support[order(impt_govt_support$proportion),]
# For ordering the graph
impt_govt_support$name <- factor(impt_govt_support$name, level=unique(as.character(impt_govt_support$name)))
# For log transformation of x axis
impt_govt_support$proportion2 <- impt_govt_support$proportion + 1.0
ggplot(impt_govt_support, aes(x=proportion, y=name)) + 
  geom_point(aes(size=transformed)) + 
  labs(x = "Proportion of Tweets supporting Net Neutrality", y = "Person mentioned in Tweet") + 
  scale_size("log(Tweets)") +
  theme_classic()
ggsave(filename="nn_govt.pdf", width=10, height=8)

res <- dbSendQuery(db, "SELECT mentions.user_mention_username as handle, 
                   mentions.user_mention as name, 
                   class, count(*) as count 
                   FROM tweets 
                   INNER JOIN mentions ON tweets.id = mentions.tweet_id 
                   WHERE about_nn == 1 
                   AND mentions.user_mention_username IS NOT NULL 
                   AND mentions.user_mention_username IN (SELECT user_mention_username 
                    FROM mentions 
                    WHERE user_mention_username != '' 
                    AND tweet_id IN (SELECT id FROM tweets WHERE about_nn == 1) 
                    GROUP BY user_mention_username 
                    ORDER BY count(*) DESC LIMIT 25
                    ) 
                   GROUP BY mentions.user_mention_username, class")
mentions <- fetch(res, n = -1)
mentions_totals <- aggregate(mentions$count, by=list(mentions$handle), FUN=sum)
colnames(mentions_totals) <- c("handle", "count")
mentions_totals <- merge(mentions, mentions_totals, by="handle", suffixes = c(".class", ".total"))
# Could use square root here again, or log
mentions_totals$transformed <- log(mentions_totals$count.total)
mentions_totals$proportion <- mentions_totals$count.class / mentions_totals$count.total
mentions_totals_support <- mentions_totals[mentions_totals$class=="s",]
mentions_totals_support <- mentions_totals_support[order(mentions_totals_support$proportion),]
# For ordering the graph
mentions_totals_support$name <- factor(mentions_totals_support$name, level=unique(as.character(mentions_totals_support$name)))
# For log transformation of x axis
mentions_totals_support$proportion2 <- mentions_totals_support$proportion + 1.0
ggplot(mentions_totals_support, aes(x=proportion, y=name)) + 
  geom_point(aes(size=transformed)) + 
  labs(x = "Proportion of Tweets supporting Net Neutrality (n.b. x-axis limits)", y = "User mentioned in Tweet") + 
  scale_size("log(Tweets)") +
  theme_classic()
ggsave(filename="nn_mentions.pdf", width=10, height=8)
