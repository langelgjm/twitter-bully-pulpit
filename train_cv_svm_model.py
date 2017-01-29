from TwitterCommon import make_config_dict, TweetDB, Document, chunks, chunks_np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.pipeline import Pipeline
from sklearn import cross_validation
import configparser
import pandas
from math import ceil
from multiprocessing import Pool

import numpy as np
from scipy import interp
import matplotlib.pyplot as plt
from sklearn import svm
from sklearn.metrics import roc_curve, auc, classification_report
from sklearn.cross_validation import StratifiedKFold

config_file = "tweets.conf"
config = configparser.ConfigParser()
config.read(config_file)
myconfig = make_config_dict(config)

db_file = myconfig['general']['db_file']

###############################################################################

def construct_document(tweet_db, tweet_id, doc_type="basic"):
    '''
    Construct a metadocument for a given tweet_id.
    '''
    mytweet = tweet_db.search_id(tweet_id)        
    mydoc = Document(mytweet)

    if doc_type == "stemmed":
        mydoc.addText(stem=True)
        mydoc.addBio(stem=True)
        mydoc.addHashtags()
        mydoc.addMentions()
        mydoc.addBaseURLs()
        mydoc.addUsername()
    else:
        mydoc.addText()
        mydoc.addBio()
        mydoc.addHashtags()
        mydoc.addMentions()
        mydoc.addBaseURLs()
        mydoc.addUsername()
    return mydoc

def get_docs(tweet_db, doc_ids, doc_type="basic"):
    '''
    Return list of text associated with the input doc_ids from the db.
    '''
    doc_list = []
    for doc_id in doc_ids:
        mydoc = construct_document(tweet_db, doc_id['id'], doc_type)
        doc_list.append(mydoc.toString())
    return doc_list

def get_doc_classes(cur, doc_ids):
    '''
    Return list of classes associated with the input doc_ids from the db.
    '''
    classes = []
    for doc_id in doc_ids:
        row = cur.execute('''SELECT class FROM manual_code WHERE id = ?''', (doc_id['id'], )).fetchone()
        classes.append(row['class'])
    return classes

def classify(chunk):
    doc_ids, doc_strings = zip(*chunk)
    doc_preds = myfit.predict(doc_strings)
    return list(zip(doc_ids, doc_preds))    

def probabilify(chunk):
    doc_ids, doc_strings = zip(*chunk)
    doc_preds = myfit.predict_proba(doc_strings)
    return list(zip(doc_ids, doc_preds))    

def class_and_prob(chunk):
    doc_ids, doc_strings = zip(*chunk)
    doc_preds = myfit.predict(doc_strings)
    doc_probs = myfit.predict_proba(doc_strings)
    return list(zip(doc_ids, doc_preds, doc_probs))
    
def get_doc_predictions_mc(tweet_db, doc_ids, mode="classes"):
    docs = []
    doc_ids_pickleable = [r['id'] for r in doc_ids]
    for row in doc_ids:
        docs.append(construct_document(tweet_db, row['id']))
    chunksize = int(ceil(len(docs) / 4))
    doc_strings = [d.toString() for d in docs]
    map_onto = []
    for chunk in chunks(list(zip(doc_ids_pickleable, doc_strings)), chunksize):
        map_onto.append(chunk)
    # Send to subprocess pool
    p = Pool(processes=4)
    if mode == "probabilities":
        map_rs = p.map(class_and_prob, map_onto, 1)
    else:
        map_rs = p.map(classify, map_onto, 1)
    # recombine the four separate lists into one big list for insertion
    preds = []
    for l in map_rs:
        preds.extend(l)
    return preds


def get_doc_class_and_prob(docs):
    docs = docs.todense()
    chunksize = int(ceil(np.shape(docs)[0] / 4))
    map_onto = []
    for chunk in chunks_np(docs, chunksize):
        map_onto.append(chunk)
    # Send to subprocess pool
    p = Pool(processes=4)
    map_rs = p.map(class_and_prob, map_onto, 1)
    # recombine the four separate lists into one big list for insertion
    preds = []
    for l in map_rs:
        preds.extend(l)
    return preds


def get_doc_class_and_prob_mc(docs):
    docs = docs.todense()
    chunksize = int(ceil(np.shape(docs)[0] / 4))
    map_onto = []
    for chunk in chunks_np(docs, chunksize):
        map_onto.append(chunk)
    # Send to subprocess pool
    p = Pool(processes=4)
    map_rs = p.map(class_and_prob, map_onto, 1)
    # recombine the four separate lists into one big list for insertion
    preds = []
    for l in map_rs:
        preds.extend(l)
    return preds

def insert_classes(tweet_db, doc_ids, classes, probs=None, class_col='class'):
    # Select the ids of all tweets that were not manually coded
    #myids = tweet_db.c.execute("SELECT id FROM tweets WHERE about_nn == 1 AND id NOT IN (SELECT id FROM manual_code WHERE class IS NOT NULL AND class != 'na')").fetchall()
    if not probs:
        for i, clas in zip(doc_ids, classes):
            tweet_db.c.execute('''UPDATE tweets SET {} = ? WHERE id = ?'''.format(class_col), (clas, i))
    else:
        for i, clas, prob in zip(doc_ids, classes, probs):
            if not 0.3 < prob[0] < 0.7:
                tweet_db.c.execute('''UPDATE tweets SET {} = ? WHERE id = ?'''.format(class_col), (clas, i))
            else:
                tweet_db.c.execute('''UPDATE tweets SET {} = ? WHERE id = ?'''.format(class_col), ('na', i))
    tweet_db.conn.commit()

def make_roc_plot(X, y, clf):
    # Run classifier with cross-validation and plot ROC curves
    cv = StratifiedKFold(y, n_folds=5, shuffle=True, random_state=None)
    
    mean_tpr = 0.0
    mean_fpr = np.linspace(0, 1, 100)
    
    for i, (train, test) in enumerate(cv):
        probas_ = clf.fit(X[train], y[train]).predict_proba(X[test])
        #probas_ = classifier.fit(X[train], y[train]).predict_proba(X[test])
        # Compute ROC curve and area the curve
        fpr, tpr, thresholds = roc_curve(y[test], probas_[:, 1])
        mean_tpr += interp(mean_fpr, fpr, tpr)
        mean_tpr[0] = 0.0
        roc_auc = auc(fpr, tpr)
        plt.plot(fpr, tpr, lw=1, label='ROC fold %d (area = %0.2f)' % (i, roc_auc))
    
    plt.plot([0, 1], [0, 1], '--', color=(0.6, 0.6, 0.6), label='Luck')
    
    mean_tpr /= len(cv)
    mean_tpr[-1] = 1.0
    mean_auc = auc(mean_fpr, mean_tpr)
    plt.plot(mean_fpr, mean_tpr, 'k--',
             label='Mean ROC (area = %0.2f)' % mean_auc, lw=2)
    
    plt.xlim([-0.05, 1.05])
    plt.ylim([-0.05, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('Receiver operating characteristics')
    plt.legend(loc="lower right")
    return plt

###############################################################################

def main():
    mydb = TweetDB(db_file)
    
    # Manually coded data
    myids = mydb.c.execute('''SELECT id FROM manual_code WHERE random_set >= 6 AND class IS NOT NULL AND class != "na"''').fetchall()
    docs = get_docs(mydb, myids, "basic")
    classes = get_doc_classes(mydb.c, myids)
    count_vect = CountVectorizer(stop_words="english", ngram_range=(1,2))
    term_freq = TfidfTransformer(use_idf=True)
    # feat_sel = SelectPercentile(f_classif, percentile=90)
    classifier = svm.SVC(kernel='linear', probability=True, C=1)

    # Take a look at the prior distribution:
    s = pandas.Series(classes)
    s.value_counts()
    y = np.array(classes)
    y = pandas.Categorical(s, categories=['s', 'o']).codes  
    X = count_vect.fit_transform(docs)
    X = term_freq.fit_transform(X)

    # ROC curve
    #plt = make_roc_plot(X, y, classifier)
    #plt.show()

    mypl = Pipeline([('cv', count_vect), 
                     ('tf', term_freq), 
                     ('clf', classifier)])    

    cv_scores = cross_validation.cross_val_score(mypl, 
        docs, classes, 
        cv=cross_validation.ShuffleSplit(len(docs),n_iter=8, train_size=0.8), 
        n_jobs=1)
    print('Raw mean CV score')
    print(np.mean(cv_scores))
    
    

    # Compare the above accuracy to that of surer probabilities
    ##X_train, X_test, y_train, y_test = cross_validation.train_test_split(X, y, test_size=0.2)
    ##global myfit
    ##myfit = classifier.fit(X_train, y_train)
    ##print(X_test)
    ##out = get_doc_class_and_prob_mc((X_test, [i['id'] for i in myids]))
    ##preds, probs = zip(*out)
    ##probs_m = np.vstack(probs)
    # Here we establish cutoff values
    ##indices = np.logical_or(probs_m[:,0] <= 0.3, probs_m[:,0] >= 0.7)
    ##preds = np.array(preds)
    ##print('CV score with weak probabilities excluded')
    ##print(np.sum(preds[indices] == y_test[indices]) / np.sum(indices))
    ##print(np.sum(indices) / len(preds))
    

    # Should try some feature selection   
    # Try marking for negation (too complicated with tweets)
    # Look at output probabilities, discard those lower than some threshold
    # Use CV to pick C

    global myfit
    myfit = mypl.fit(docs, classes)
    
###############################################################################    



###############################################################################

    # Select the ids of all tweets that were not manually coded
    myids = mydb.c.execute("SELECT id FROM tweets WHERE about_cc == 1 AND id NOT IN (SELECT id FROM manual_code WHERE class IS NOT NULL AND class != 'na' AND random_set >= 6)").fetchall()
    ## mypreds = get_doc_predictions_mc(mydb, myids)
    mypreds = get_doc_predictions_mc(mydb, myids, "probabilities")
    ids, classes, probs = zip(*mypreds)
    prob_o, prob_s = zip(*probs)
    
    #plt.hist(prob_s, 20)
    #plt.show()
    # So what if we discarded all predictions of support less certain than 90%
    # And discarded all oppose less certain than 90%
    
    # ids, classes = zip(*mypreds)

    print(pandas.Series(classes).value_counts())

    # TODO: insert_classes must be modified so that it refers to a different column for climate change tweets!!!
    insert_classes(mydb, ids, classes, probs, class_col='class_cc')

    # Add in the classes of manually coded tweets
    (ids, classes) = zip(*mydb.c.execute("SELECT id, class FROM manual_code WHERE class IS NOT NULL AND class != 'na'").fetchall())
    insert_classes(mydb, ids, classes, probs=None, class_col='class_cc')
    mydb.close()
    
if __name__ == "__main__":
    main()
