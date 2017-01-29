setwd("data")
mycolClasses = c("factor", "numeric", "numeric", "numeric", "character", 
                 "character", "character", "character", "numeric", "character")
tweets <- read.csv("1k_train_classes_only.csv", header=TRUE, colClasses=mycolClasses)

table(tweets$class)[1:3])
prop.table(matrix(table(tweets$class)[1:3]))
table(tweets$class)[5:7])
prop.table(matrix(table(tweets$class)[5:7]))
prop.test(362,470, conf.level=0.99, p=0.5)
prop.test(456,529, conf.level=0.99, p=0.5)

# Now let's get the date data, graph tweets per day, and split the sample based on 
# before and after the statement to see if there is a difference in proportions
tweets$datetime <- as.POSIXct(tweets$posted_time, tz = "GMT", format="%m/%d/%Y %H:%M:%S")
tweets$date <- as.Date(tweets$datetime)

alldata <- table(tweets$date)
nndata <- table(tweets[tweets$class %in% c("nns", "nno", "nnn"),"date"])
ccdata <- table(tweets[tweets$class %in% c("ccb", "ccd", "ccn"),"date"])
xlabels <- names(alldata)
xdates <- as.Date(xlabels)
xlabels <- strftime(xdates, format="%b %d")
pdf("sample_timeline.pdf", width=6, height=4)
par(mar=c(4,4,1,1))
plot(alldata, type="l", ylab="Number of Tweets", xaxt="n")
axis(1, at=seq(which.min(xdates),which.max(xdates),1), cex.axis=0.75, las=2, labels=xlabels)
lines(nndata, col="red", type="l")
lines(ccdata, col="green", type="l")
legend(1,150, legend=c("Total", "Climate Change", "Net Neutrality"), fill=c("black", "green", "red"), border=NA, bty="n", cex=0.75)
dev.off()

nndata_before <- table(tweets[tweets$class %in% c("nns", "nno", "nnn") & tweets$date < as.Date("2014-11-10"),"class"])
nndata_after <- table(tweets[tweets$class %in% c("nns", "nno", "nnn") & tweets$date > as.Date("2014-11-10"),"class"])
nndata_matrix <- matrix(c(nndata_before[6:7], nndata_after[6:7]), nrow=2)
prop.test(nndata_matrix)

ccdata_before <- table(tweets[tweets$class %in% c("ccb", "ccd", "ccn") & tweets$date < as.Date("2014-11-10"),"class"])
ccdata_after <- table(tweets[tweets$class %in% c("ccb", "ccd", "ccn") & tweets$date > as.Date("2014-11-10"),"class"])
ccdata_matrix <- matrix(c(ccdata_before[1:2], ccdata_after[1:2]), nrow=2)
prop.test(ccdata_matrix)