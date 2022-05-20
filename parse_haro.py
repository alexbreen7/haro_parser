from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from email.mime.text import MIMEText
import base64
from base64 import urlsafe_b64encode
import os
import time
from twilio.rest import Client


#helper function that sets up the credentials and connects to gmail
def setup_credentials(token_path, key_path):
    API_scopes = ['https://mail.google.com/']
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, API_scopes)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                key_file, API_scopes)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    gmail_service = build("gmail", "v1", credentials=creds)
    return gmail_service

#function to send a text message using the twilio API
def send_text(to,content):
    message = twilio_client.messages.create(
    to=to, 
    from_= {INSERT PHONE NUMBER},
    body=content)

#the token/secret to the email account
secret = os.environ.get({PATH TO EMAIL SECRET})
token = os.environ.get({PATH TO EMAIL TOKEN})

#connecting to gmail
service = setup_credentials(token_path=token, key_path=secret)

#connecting to Twilio
account_sid = os.environ.get('twilio_sid')
auth_token  = os.environ.get('twilio_token')
twilio_client = Client(account_sid, auth_token)


#Query for the emails from HARO
#only send messages sent today. 
yesterday = datetime.now() + timedelta(days= -1)
date_filter = yesterday.strftime('%Y/%m/%d')
q = f'from:(haro@helpareporter.com) after:{date_filter}'
#Function to get the latest email from haro@helpareporter.com
def get_message():
    #Getting a list of the messages that match the query
    messages = service.users().messages().list(
            userId="me", q=q).execute()
    #Getting the ID of the most recent message
    mid = messages['messages'][0]['id']
    #querying the contents of that message.
    msg = service.users().messages().get(userId="me",id = mid,format='raw').execute()
    
    return msg

#Get the most recent message
msg = get_message()
#check the time it was received
rec_time = msg['internalDate']
counter = 0
#If the most recent HARO email was sent more than an hour ago, we haven't gotten the new one yet. Retry every 1 minute up to 10 times and keep checking. 
while time.time() - int(rec_time[:-3]) > 3600:
    msg = get_message()
    rec_time = msg['internalDate']
    time.sleep(60)
    counter+=1
    #we don't want this to go on forever, if the email hasn't come in 10 minutes, give up. 
    if counter == 10:
        1/0

#encoding the message as a string
msg_str = base64.urlsafe_b64decode(msg['raw'].encode('ASCII'))

#the queries are separated by a bunch of dashes so let's split them up
splits = str(msg_str).split('-----------------------------------')
#but the first query is separated by stars. Let's extract just the query and add it to the end of the list
splits.extend(splits[0].split('****************************')[1])
#let's drop the first entry (all the summary stuff, everything before the 2nd query)
splits = splits[1:]

#establishing the keywords we want to search for
keywords = [{INSERT_KEYWORDS HERE}]

#parsing out the subject
subject = str(msg_str).split('\\r\\nSubject: ')[1].split('\\r\\')[0]

#iterating through all the requests and checking if any of the keywords are in it. 
matches = []
for query in splits:
    #the address marks the end of the queries in the email. When we see that, we want to stop looking
    if  '12051 Indian Creek Ct., Beltsville, MD 20705, USA' in query:
        break
    for keyword in keywords:
        if keyword.lower() in query.lower():
            matches.append({'kw':keyword, 'query':query})
            #we don't want to alert multiple times on the same message 
            break

#Now we iterate through the matches, clean up the text, and send a text to the user. 
for match in matches:
    #We need to parse the email query to remove a lot of the gunk
    elements = [x for x in match['query'].split('\\r\\n') if x != '']
    #Now we want to find the summary and query/request.
    #The summary is easy, it just has the word summary in it. It normally isn't more than one element. 
    #The query/request is normally multiple elements, the first one is the one that has the word query, and the last is one before the word "Requirements". 
    #we need to establish default values for the start of the request and the end of it. (In case "Query" or "Request" aren't found).
    r_start = 0
    r_end = len(elements)
    for e in elements:
        if 'Summary:' in e:
            summary = e
    
    kw = match['kw']
    
    msg = f'New Match for {kw} in {subject}: {summary}'
    
    send_text({YOUR PHONE NUMBER},msg)
    time.sleep(5)
