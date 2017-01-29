coders <- c("gabe", "colin", "cory")

csv_reader <- function(coder) {
  path <- paste0("data/tocode_", coder, "_coded.csv")
  read.csv(path, stringsAsFactors=FALSE, header=TRUE)
}

df_list <- sapply(coders, csv_reader, simplify=FALSE)
icr <- Reduce(function(...) merge(..., by="id_text", all=TRUE), df_list)
names(icr)[2:4] <- coders 

# Summarize results of coding
lapply(icr[2:4], function(x) summary(as.factor(x)))

# Pairwise combos of coders
combos <- combn(coders, m=2, simplify=FALSE)

# Raw pairwise ICR
# Of all units shared in common between coders, what % coded same
icr_pairs <- function(x, df, all=TRUE) {
  # Subsetting of df to exclude "na" codes when doing net ICR
  if (all==FALSE) {
    df <- df[df[,x[1]] != "na" & df[,x[2]] != "na", ]    
  }
  agreed <- sum(df[,x[1]] == df[,x[2]], na.rm=TRUE)
  total <- sum(! (is.na(df[,x[1]]) | is.na(df[,x[2]])))
  agreed / total
}
sapply(combos, icr_pairs, df=icr)

# Raw three-way ICR
icr_threeway <- function(df) {
  agreed <- sum(apply(df[2:4], 1, function(x) length(unique(x))==1))
  total <- nrow(df)
  agreed / total  
}
icr_triplets <- icr[apply(is.na(icr), 1, function(x) sum(x)==0),]
icr_threeway(icr_triplets)

# Net pairwise ICR
# Of all units shared in commmon and not coded na, what % coded same
sapply(combos, icr_pairs, df=icr, all=FALSE)

# Net three-way ICR
icr_triplets_complete <- icr_triplets[! apply(icr_triplets[2:4], 1, function(x) any(x == "na")),]
icr_threeway(icr_triplets_complete)