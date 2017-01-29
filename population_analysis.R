setwd("data")

# produced by
# select posted_date, count(*) from tweets group by posted_date;
totals <- read.csv("all_by_date.csv", stringsAsFactors=FALSE, header=FALSE)
colnames(totals) <- c("date", "total_freq")
# produced by
# select posted_date, count(*) from tweets where about_nn == 1 group by posted_date;
nn <- read.csv("nn_by_date.csv", stringsAsFactors=FALSE, header=FALSE)
colnames(nn) <- c("date", "nn_freq")
# produced by
# select posted_date, count(*) from tweets where about_cc == 1 group by posted_date;
cc <- read.csv("cc_by_date.csv", stringsAsFactors=FALSE, header=FALSE)
colnames(cc) <- c("date", "cc_freq")

df <- merge(cc, nn, by="date", all=TRUE)
df <- merge(df, totals, by="date", all=TRUE)

# Fix dates by 0-padding the day
df$date <- sapply(strsplit(df$date, "-"), function(x) if (nchar(x[2]) == 1) paste0(x[1], "-0", x[2], "-", x[3]) else paste(x[1], x[2], x[3], sep="-") )
df$date <- as.Date(df$date, format="%m-%d-%Y")
df <- df[order(df$date), ]

###########################
# For full dataset timeline
###########################

pdf("timeline.pdf", width=6, height=4)
xvals <- seq(which.min(df$date),which.max(df$date),1)
xlabs <- strftime(df$date, format="%b %d")
par(mar=c(4,4,1,1))
plot(xvals, df$total_freq, ylim=c(0,120000), type="l", xlab="", ylab="Number of Tweets", xaxt="n", yaxt="n", bty="n", lwd=2)
axis(1, at=xvals, cex.axis=0.75, las=2, labels=xlabs)
axis(2, at=seq(0,120000,20000), cex.axis=0.75, las=2, labels=paste0(seq(0,120,20), "k"))
lines(xvals, df$nn_freq, col="red", type="l", lwd=2)
lines(xvals, df$cc_freq, col="green", type="l", lwd=2)
legend(1,120000, legend=c("Total", "Climate Change", "Net Neutrality"), fill=c("black", "green", "red"), border=NA, bty="n", cex=0.75)
dev.off()

#########################################
# For creating hashtag frequency tables
#########################################

pre <- read.csv("nn_hashtags_pre_nov10.csv", stringsAsFactors=FALSE, header=FALSE)
colnames(pre) <- c("Hashtag", "Frequency")
pre_top25 <- head(pre[order(-pre$Frequency),], 25)
post <- read.csv("nn_hashtags_post_nov10.csv", stringsAsFactors=FALSE, header=FALSE)
colnames(post) <- c("Hashtag", "Frequency")
post_top25 <- head(post[order(-post$Frequency),], 25)

# This also highlights some column headers, not sure why, docs say it shouldn't...
my_sanitizer <- function(x) {
  my_intersection <- intersect(pre_top25$Hashtag, post_top25$Hashtag)
  my_highlights <- sapply(x, function(x) ! x %in% my_intersection)
  sapply(names(my_highlights), function(x) ifelse(my_highlights[x], paste0("\\hl{", x, "}"), x))
}

library(xtable)
ranks <- data.frame(Rank=1:25)
xt <- xtable(cbind(ranks, pre_top25, post_top25))
print(xt, include.rownames=FALSE, sanitize.text.function=my_sanitizer)

pre <- read.csv("cc_hashtags_pre_nov10.csv", stringsAsFactors=FALSE, header=FALSE)
colnames(pre) <- c("Hashtag", "Frequency")
pre_top25 <- head(pre[order(-pre$Frequency),], 25)
post <- read.csv("cc_hashtags_post_nov10.csv", stringsAsFactors=FALSE, header=FALSE)
colnames(post) <- c("Hashtag", "Frequency")
post_top25 <- head(post[order(-post$Frequency),], 25)

library(xtable)
ranks <- data.frame(Rank=1:25)
xt <- xtable(cbind(ranks, pre_top25, post_top25))
print(xt, include.rownames=FALSE)

#########################################
# For 60 minute plot of tweets per minute
#########################################

nov10hour <- read.csv("nn_timeofday_dist_nov10.csv", stringsAsFactors=FALSE, header=FALSE)
colnames(nov10hour) <- c("Time", "Frequency")
nov03hour <- read.csv("nn_timeofday_dist_nov03.csv", stringsAsFactors=FALSE, header=FALSE)
colnames(nov03hour) <- c("Time", "Frequency")
nov10hour$Time <- as.POSIXct(paste("2014-11-10", nov10hour$Time), tz="GMT")
nov03hour$Time <- as.POSIXct(paste("2014-11-03", nov03hour$Time), tz="GMT")

pdf("hourline.pdf", width=6, height=4)
xvals <- seq(1,60,1)
labxvals <- seq(1,60,2)
xlabs <- strftime(nov10hour$Time[labxvals], format="%H:%M")
par(mar=c(4,4,1,1))
plot(xvals, nov10hour$Frequency, ylim=c(0, 250), type="l", col="red", xlab="", ylab="Number of Tweets", xaxt="n", yaxt="n", bty="n", lwd=2)
axis(1, at=labxvals, cex.axis=0.75, las=2, labels=xlabs)
axis(2, at=seq(0,225,25), cex.axis=0.75, las=2, labels=seq(0,225,25))
lines(xvals, nov03hour$Frequency, type="l", col="black", lwd=2)
legend(1,225, legend=c("Nov 10", "Nov 3"), fill=c("red", "black"), border=NA, bty="n", cex=0.75)
dev.off()

#########################################
# For creating word frequency tables
#########################################

pre <- read.csv("nn_pre_vocab.csv", stringsAsFactors=FALSE, header=FALSE)
colnames(pre) <- c("Stem", "Frequency")
pre_top25 <- head(pre[order(-pre$Frequency),], 25)
post <- read.csv("nn_post_vocab.csv", stringsAsFactors=FALSE, header=FALSE)
colnames(post) <- c("Stem", "Frequency")
post_top25 <- head(post[order(-post$Frequency),], 25)

# This also highlights some column headers, not sure why, docs say it shouldn't...
my_sanitizer <- function(x) {
  my_intersection <- intersect(pre_top25$Stem, post_top25$Stem)
  my_highlights <- sapply(x, function(x) ! x %in% my_intersection)
  sapply(names(my_highlights), function(x) ifelse(my_highlights[x], paste0("\\hl{", x, "}"), x))
}

library(xtable)
ranks <- data.frame(Rank=1:25)
xt <- xtable(cbind(ranks, pre_top25, post_top25))
print(xt, include.rownames=FALSE, sanitize.text.function=my_sanitizer)

pre <- read.csv("cc_pre_vocab.csv", stringsAsFactors=FALSE, header=FALSE)
colnames(pre) <- c("Stem", "Frequency")
pre_top25 <- head(pre[order(-pre$Frequency),], 25)
post <- read.csv("cc_post_vocab.csv", stringsAsFactors=FALSE, header=FALSE)
colnames(post) <- c("Stem", "Frequency")
post_top25 <- head(post[order(-post$Frequency),], 25)

library(xtable)
ranks <- data.frame(Rank=1:25)
xt <- xtable(cbind(ranks, pre_top25, post_top25))
print(xt, include.rownames=FALSE, sanitize.text.function=my_sanitizer)
