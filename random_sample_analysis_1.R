setwd("data")

library(stringr)

# produced by
df <- read.csv("1k_train_rep.csv", stringsAsFactors=FALSE, header=TRUE)

df$date <- sapply(df$X.M..posted_time, function(x) sub(str_sub(x, start=-9), '', x))
df$date <- as.Date(df$date, format="%m/%d/%Y")
df <- df[order(df$date), ]
df$pre <- df$date < as.Date('2014-11-10')
df$post <- df$date > as.Date('2014-11-10')

aggregate(df$date, by=list(df$classification, df$pre), length)

prop.test(t(prop.table(matrix(c(172, 11, 284, 18), ncol=2), margin=2)))
prop.test(t(prop.table(matrix(c(333, 36, 29, 2), ncol=2), margin=2)))