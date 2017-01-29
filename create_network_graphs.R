library(sqldf)
library(igraph)
library(scales)
library(parallel)

setwd("")

# Here we set two thresholds:
# mention_thresh determines how many large, labeled nodes we will have
# by establishing a cutoff for the minimum number of mentions for a given user 
# across the time period among tweets discussing NN.
# user_thresh determines which normal users (i.e., those that are not large nodes) 
# to include by establishing a cutoff for the minimum number of tweets 
# from a given user across the time period among tweets discussing NN.
# Note that setting user_thresh to a low value will drastically increase 
# the size of the graph and the time required to plot it.
mention_thresh <- 500
user_thresh <- 2

db <- dbConnect(SQLite(), dbname="data/tweets.sqlite")

# Example query to retrieve all user -> mention relationships (there are a lot)
# res <- dbSendQuery(db, "SELECT username, 
#   mentions.user_mention_username AS mention 
#   FROM tweets 
#   INNER JOIN mentions ON tweets.id = mentions.tweet_id 
#   WHERE about_nn == 1 
#   AND mentions.user_mention_username != '' 
#   ORDER BY username")

# query to retrieve selected user -> mention relationships
query_string <- paste("SELECT username, 
  mentions.user_mention_username AS mention, 
  count(*) AS weight 
  FROM tweets 
  INNER JOIN mentions ON tweets.id = mentions.tweet_id 
  WHERE about_nn == 1 
    AND mention != '' 
    AND mention IN (SELECT user_mention_username 
      FROM mentions 
      WHERE tweet_id IN (SELECT id 
        FROM tweets 
        WHERE about_nn == 1) 
      GROUP BY user_mention_username 
      HAVING count(user_mention_username) >=", mention_thresh, ")
    AND username IN (SELECT username 
      FROM tweets 
      WHERE about_nn == 1 
      GROUP BY username 
      HAVING count(username) >=", user_thresh, ")
  GROUP BY username, mention 
  ORDER BY username")
res <- dbSendQuery(db, query_string)
u_mt <- fetch(res, n = -1)

# Build vector of number of MTs for unique large nodes
mt_num <- aggregate(username ~ mention, data=u_mt, FUN=length)

# query to retrieve counts of class assignments grouped by username and class
# for users meeting the requirements established above
query_string <- paste("SELECT username, 
  class as class, 
  count(*) as count 
  FROM tweets 
  INNER JOIN mentions ON tweets.id = mentions.tweet_id 
  WHERE about_nn == 1 
    AND mentions.user_mention_username != '' 
    AND username IN (SELECT username 
      FROM tweets 
      WHERE about_nn == 1 
      GROUP BY username 
      HAVING count(username) >=", user_thresh, ") 
  OR about_nn == 1 
    AND username IN (SELECT user_mention_username 
    FROM mentions 
    WHERE user_mention_username != '' 
      AND user_mention_username IN (SELECT user_mention_username 
        FROM mentions 
        WHERE tweet_id IN (SELECT id 
          FROM tweets 
          WHERE about_nn == 1) 
        GROUP BY user_mention_username 
        HAVING count(user_mention_username) >=", mention_thresh, "))
  GROUP BY username, class 
  ORDER BY username ASC, count DESC")
res <- dbSendQuery(db, query_string)
u_class <- fetch(res, n = -1)

# Note that the above query also provides a good way of assessing sanity of 
# classifications: compare proportion of tweets from a 
# given user that are classified the same way.

# Assign an overall class to distinct users by dropping 
# the second of each row with a duplicate username.
# Because of query ordering, the second of each pair of rows 
# will have the class and count with fewer values.
u_class_maj <- u_class[! duplicated(u_class$username), ]

g <- graph.data.frame(u_mt, directed=TRUE)

nodeSize <- function(n) {
  if (! n %in% mt_num$mention) {
    1
  }
  else {
    mt_num[mt_num$mention==n, "username"]
  }
}
v_sizes = unlist(lapply(V(g)$name, nodeSize))
V(g)$size = log(v_sizes) * 2.0

nodeColor <- function(n) {
  if (n %in% mt_num$mention) {
  # For large, mention nodes, pick a random transparent color and less transparent border
    random_color = sample(colors(), 1)
    node_color = rgb(t(col2rgb(random_color)), alpha = 127, maxColorValue = 255)
    frame_color = rgb(t(col2rgb(random_color)), alpha = 255, maxColorValue = 255)
  } else {
  # For normal user nodes, pick a color according to classification and no border
    class = u_class_maj[u_class_maj$username==n, "class"]
    # If not found we get a logical vector of length 0
    if (length(class) == 0) {
      # This should never happen
      node_color = "white"
    } else if (class == "s") {
      node_color = "green3"
    } else {
      node_color = "red3"
    }
    frame_color = NA
  }
  # Return a list of the selected node color and border color
  list('node_color' = node_color, 'frame_color' = frame_color)
}
v_colors_list = mclapply(V(g)$name, nodeColor, mc.cores = 4)
v_colors_mat = matrix(unlist(v_colors_list), ncol=2, byrow=TRUE)
V(g)$color = v_colors_mat[,1]
V(g)$frame.color = v_colors_mat[,2]

nodeLabel <- function(n) {
  if (n %in% mt_num$mention) {
    n
  } else {
    NA
  }
}
v_labels = unlist(lapply(V(g)$name, nodeLabel))
V(g)$label = v_labels

edgeColor <- function(n) {
  class = u_class_maj[u_class_maj$username==n, "class"]
  if (class == "s") {
    "green2"
  } else if (class == "o") {
    "red2"
  } else {
    # This should never happen
    "blue"
  }
}
edgeAlpha <- function(x, w) {
  rgb(t(col2rgb(x)), alpha = w, maxColorValue = 255)
}
e_colors = unlist(mclapply(get.edgelist(g)[,1], edgeColor, mc.cores=4))
weight_scaled = rescale(log(E(g)$weight), to=c(32,255))
e_alphas = mapply(edgeAlpha, e_colors, weight_scaled)
E(g)$color = e_alphas

plotGraph <- function(layout, g, file_name_prefix) {
  file_name = paste0(file_name_prefix, layout, ".pdf")
  pdf(file_name, width=18, height=18)
  set.seed(1)
  plot(g, 
       vertex.label.color = "black", 
       vertex.label.family = "sans", 
       vertex.label.cex = 0.375, 
       edge.arrow.size=0, 
       edge.width = log(E(g)$weight) + 0.5, 
       layout = get(layout))
  dev.off()
}

# For testing various layouts, this creates a list of all available 
# layouts and excludes the ones that don't make sense for this network
# layouts = grep("^layout\\.", ls("package:igraph"), value=TRUE)
# layouts = layouts[! layouts %in% c("layout.norm", "layout.auto", 
#                                    "layout.circle", "layout.bipartite", 
#                                    "layout.merge", "layout.reingold.tilford", 
#                                    "layout.spring", "layout.sugiyama")]
# After testing, these two work best, although kamada.kawai takes much longer
layouts = c("layout.fruchterman.reingold", "layout.kamada.kawai")

lapply(layouts, plotGraph, g, "graph_")