"""
 file:        facialEmotionAnlysis.py
 author:      Daniel Vance
 date:        20160619
 description: An analysis of media images and influence on public opinion polls
              for presidential candidates

"""

""" NOTES
Project Oxford API key instructions:
    To use this notebook, you will need to get keys to Emotion API. Visit 
    "http://www.projectoxford.ai/emotion", and then the "Try for free" button. 
    On the "Sign in" page, use your Microsoft account to sign in and you will 
    be able to subscribe to Emotion API and get free keys (Code of Conduct and 
    TOS). After completing the sign-up process, paste your key into the 
    variables section below. (Either the primary or the secondary key works.)

Google Custom Search API key instructions:
    A HOWTO can be found at:
 https://drive.google.com/open?id=1Q48j-E1w4QFmJXwyA0T4uMVBtFlTZiR5VYj8f_eH8Pw
"""

# Imports
import time 
import requests
import cv2
import operator
import numpy as np
import pprint
from datetime import datetime
from datetime import date, timedelta
from collections import Counter
from googleapiclient.discovery import build

# Variables
startWeek   = 1
endWeek     = 47
numOfPages  = 4  # Two pages of results give 20 results a week. Adjust this to 
                 # get more or less data per week.
_candidate  = ""  # Canidates Full Name ex: "Bernie Sanders"
_key        = ''  #### PASTE YOUR MICROSOFT EMOTION API KEY HERE ####
_gKey       = ''  #### PASTE YOUR GOOGLE API KEY HERE ####
_cx         = '009287171158739071908:f6cgoxrx81s' # Custom Search Engine using 39 political sites
_url        = 'https://api.projectoxford.ai/emotion/v1.0/recognize' 
_maxNumRetries = 3                                



# Image Class for keeping track of the images
class Image:
    def __init__(self, candidate, srcSite, imageURL, imageEmotions, imgWeek, imgDate):
        self.candidate = candidate
        self.site      = srcSite
        self.imageURL  = imageURL
        self.emotions  = imageEmotions # Dictionary of Emotions Scores
        self.week      = imgWeek 
        self.date      = imgDate

# Helper Functions
def processRequest( json, data, headers ):

    """
    Helper function to process the request to Project Oxford

    Parameters:
    json: Used when processing images from its URL. See API Documentation
    data: Used when processing image read from disk. See API Documentation
    headers: Used to pass the key information and the data type request
    """
    retries = 0
    result = None

    while True:

        response = requests.request( 'post', _url, json = json, data = data, headers = headers, params = None )

        if response.status_code == 429: 

            print "Message: %s" % ( response.json()['error']['message'] )

            if retries <= _maxNumRetries: 
                time.sleep(1) 
                retries += 1
                continue
            else: 
                print 'Error: failed after retrying!'
                break

        elif response.status_code == 200 or response.status_code == 201:

            if 'content-length' in response.headers and int(response.headers['content-length']) == 0: 
                result = None 
            elif 'content-type' in response.headers and isinstance(response.headers['content-type'], str): 
                if 'application/json' in response.headers['content-type'].lower(): 
                    result = response.json() if response.content else None 
                elif 'image' in response.headers['content-type'].lower(): 
                    result = response.content
        else:
            print "Error code: %d" % ( response.status_code )
            print "Message: %s" % ( response.json()['error']['message'] )

        break
        
    return result

def detectEmotion(urlImage):
    headers = dict()
    headers['Ocp-Apim-Subscription-Key'] = _key
    headers['Content-Type'] = 'application/json' 

    json = { 'url': urlImage } 
    data = None

    result = processRequest( json, data, headers )
    
    return result

def checkDuplicate(newsImage, masterList):
    if not masterList:
        masterList.append(newsImage)
    else:
        for obj in masterList:
            if obj.imageURL == newsImage.imageURL:
                print  "Duplicate Image", obj.imageURL
                break
        else:
            masterList.append(newsImage)
    return masterList

def getEmotions(numOfWeeks, masterList):
    emotionList = ["sadness", "contempt", "disgust", "anger", "surprise", "fear", "happiness", "neutral", "count"]
    masterDict  = dict()

    
    for week in range(1, numOfWeeks + 1):
        siteDict    = dict()
        siteCounter = dict()
        for obj in masterList:
            key = obj.site
            if obj.week == week:
                if key in siteDict:
                    siteCounter[key] += 1
                    siteA = Counter(obj.emotions)
                    siteB = Counter(siteDict[key])
                    sumOfEmotions = siteA + siteB
                    siteDict[key] = sumOfEmotions
                else:
                    siteDict[key] = obj.emotions
                    siteCounter[key] = 1
            else:
                continue
        for key, value in siteDict.iteritems():
            tmpDict = dict()
            for emotion in emotionList:
                if emotion == "count":
                    tmpDict[emotion] = siteCounter[key]
                else:
                    try:
                        currentEmotionScore = siteDict[key][emotion]
                        tmpDict[emotion] = currentEmotionScore / siteCounter[key]
                    except:
                        continue
            siteDict[key] = tmpDict
        masterDict[week] = siteDict
    return masterDict
    

# SCRIPT PORTION THAT PULLS IT ALL TOGETHER
clintonMasterDict = dict()   # Dict by weeek of sites of emotions
sandersMasterDict = dict()
trumpMasterDict   = dict()

clintonMasterList = list()   # Lists of Image class elements for the candidate
sandersMasterList = list()
trumpMasterList   = list()
searchResult      = dict()   # Dictionary to hold the returned JSON search information


numOfWeeks   = 48
numOfResults = 10 * numOfPages  # Must be a multiple of 10, so multiply the number of "pages" by the number of results per page
candidates   = [_candidate]     # ["Hillary Clinton", "Bernie Sanders", "Donald Trump"]
todayDate    = date.today()

service = build("customsearch", "v1", developerKey=_gKey)  

for candidate in candidates:
    for i in range(startWeek, endWeek + 1):
        for j in range(1, numOfResults, 10):
            try:
                searchResult = service.cse().list( q=candidate,               # Query
                                                   # searchType="image",        # Image Search
                                                   imgType="face",            # Face images
                                                   dateRestrict='w' + str(i), # Restrict date by weeks from today
                                                   cx=_cx,             # custom search engine
                                                   filter='0',                # do not allow duplicates
                                                   start=j,                   # results "page" to start on
                                                   sort="date:a"              # sort by date ascending
                                                 ).execute()
            except:
                print "Query did not succeed"
                continue
            for k in range(10):
                try:
                    imgSource = searchResult["items"][k]["displayLink"]
                    # imgURL = searchResult["items"][k]["link"]  # This is for Image Search
                    imgURL = searchResult["items"][k]["pagemap"]["cse_image"][0]["src"] # This is for default search
                    weekPublished = numOfWeeks - i
                    datePublished = todayDate - timedelta(days=(i * 7))
                    
                    results = detectEmotion(imgURL)
                    time.sleep(12)  # Emotion API only allows 5 requests per minute
                except:      # if there is an error trying to get any on the needed data, skip the search result
                    print "Search Result was missing an image"
                    continue            

                if not results:
                    print "Failed to find a face in the image"
                    continue
                try:
                    emotionScores = results[0]["scores"]
                except:    
                    # emotionScores = results[0][0]["scores"] # Select the emotion for the first face in the image results
                    print "Image has more than one face"
                
                newsImage = Image(candidate, imgSource, imgURL, emotionScores, weekPublished, datePublished)
                if candidate == "Hillary Clinton":
                    clintonMasterList = checkDuplicate(newsImage, clintonMasterList)                            
                if candidate ==  "Bernie Sanders":
                    sandersMasterList = checkDuplicate(newsImage, sandersMasterList)
                if candidate ==  "Donald Trump":
                    trumpMasterList = checkDuplicate(newsImage, trumpMasterList)
    
    # Write out all the data from the candidates list
    masterList = [clintonMasterList, sandersMasterList, trumpMasterList]
    outFile = '' + candidate + "_full_output.csv"
    csvFile = open(outFile, 'a')
    headerString = 'week, date, website, count, sadness, contempt, disgust, anger, surprise, fear, happiness, neutral, imageUrl\n'
    csvFile.write(headerString)
    for imageList in masterList:
        for image in imageList:
            weekAsDate = image.date.strftime('%m/%d/%Y') 
            count          = 1
            sadnessScore   = image.emotions["sadness"]
            contemptScore  = image.emotions["contempt"]
            disgustScore   = image.emotions["disgust"]
            angerScore     = image.emotions["anger"]
            surpriseScore  = image.emotions["surprise"]
            fearScore      = image.emotions["fear"]
            happinessScore = image.emotions["happiness"]
            neutralScore   = image.emotions["neutral"]
            emotionScoreString = '' + str(count) + ',' + \
                                      str(sadnessScore)   + ',' + str(contemptScore) + ',' + str(disgustScore) + ',' + \
                                      str(angerScore)     + ',' + str(surpriseScore) + ',' + str(fearScore)    + ',' + \
                                      str(happinessScore) + ',' + str(neutralScore) 
            writeString = '' + str(image.week) + ',' + weekAsDate + ',' + image.site + ',' + emotionScoreString + ',' + image.imageURL + '\n'
            csvFile.write(writeString)
    csvFile.close()            
    # <candidate>MasterDict will be a dict of {week# : {website : { emotion: emotionScore}}}
    if candidate ==  "Hillary Clinton":
        clintonMasterDict = getEmotions(numOfWeeks, clintonMasterList)
    if candidate ==  "Bernie Sanders":
        sandersMasterDict = getEmotions(numOfWeeks, sandersMasterList)
    if candidate ==  "Donald Trump":
        trumpMasterDict = getEmotions(numOfWeeks, trumpMasterList)
    
    masterDictList = [clintonMasterDict, sandersMasterDict, trumpMasterDict]
    # Write out to a csv file        
    outFile = '' + candidate + "_output.csv"
    csvFile = open(outFile, 'a')
    headerString = 'week, date, website, count, sadness, contempt, disgust, anger, surprise, fear, happiness, neutral\n'
    csvFile.write(headerString)
    for candidateDict in masterDictList:
        for week, valueDict in candidateDict.iteritems():
            weekAsDate = todayDate - timedelta(days=((numOfWeeks - week) * 7)) 
            weekAsDate = weekAsDate.strftime('%m/%d/%Y') 
            emotionScoreString = ''
            for site, emotionDict in valueDict.iteritems():
                count          = emotionDict["count"]
                sadnessScore   = emotionDict["sadness"]
                contemptScore  = emotionDict["contempt"]
                disgustScore   = emotionDict["disgust"]
                angerScore     = emotionDict["anger"]
                surpriseScore  = emotionDict["surprise"]
                fearScore      = emotionDict["fear"]
                happinessScore = emotionDict["happiness"]
                neutralScore   = emotionDict["neutral"]
                emotionScoreString = '' + str(count) + ',' + \
                                          str(sadnessScore)   + ',' + str(contemptScore) + ',' + str(disgustScore) + ',' + \
                                          str(angerScore)     + ',' + str(surpriseScore) + ',' + str(fearScore)    + ',' + \
                                          str(happinessScore) + ',' + str(neutralScore) 
                writeString = '' + str(week) + ',' + weekAsDate + ',' + site + ',' + emotionScoreString + '\n'
                csvFile.write(writeString)
    csvFile.close()
print "Script Completed"

                    