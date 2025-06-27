import os
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import base64
from email.message import EmailMessage
from bs4 import BeautifulSoup
from agent.llm import get_email_summary, write_email

def create_service(client_secret_file, API_SERVICE_NAME, API_VERSION, *SCOPES, prefix=''):
    CLIENT_SECRET_FILE = client_secret_file
    SCOPES = [scope for scope in SCOPES]

    creds = None
    working_dir = os.getcwd()
    token_dir = 'token_files'
    token_file = f'token_{API_SERVICE_NAME}_{API_VERSION}{prefix}.json'

    # Creating token folder
    if not os.path.exists(os.path.join(working_dir, token_dir)):
        os.mkdir(os.path.join(working_dir, token_dir))

    # Loading existing credentials
    token_path = os.path.join(working_dir, token_dir, token_file)
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # If no valid creds, initiate login flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=8080)
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    try:
        service = build(API_SERVICE_NAME, API_VERSION, credentials=creds, static_discovery=False)
        print(f'{API_SERVICE_NAME} {API_VERSION} service created successfully')
        return service
    except Exception as e:
        print(e)
        print(f'Failed to create service instance for {API_SERVICE_NAME}')
        os.remove(token_path)
        return None
    
def list_recent_emails(service, me, max_results, label_ids=['INBOX']):
    if not max_results:
        max_results = 5
    results = service.users().messages().list(
        userId=me,
        labelIds=label_ids,
        maxResults=max_results
    ).execute()
    messages = results.get('messages', [])

    email_summaries = []

    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()

        headers = msg_data['payload'].get('headers', [])
        subject = sender = date = None

        for h in headers:
            name = h['name'].lower()
            if name == 'subject':
                subject = h['value']
            elif name == 'from':
                sender = h['value']
            elif name == 'date':
                date = h['value']

        # snippet = msg_data.get('snippet', '')

        # Body
        body = ""
        def get_body(payload):
            if 'parts' in payload:
                for part in payload['parts']:
                    result = get_body(part)
                    if result:
                        return result
            elif payload.get('mimeType') in ['text/plain', 'text/html']:
                data = payload['body'].get('data')
                if data:
                    decoded = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    return decoded
            return ""

        body = get_body(msg_data['payload'])
        soup = BeautifulSoup(body, 'html.parser')
        text_content = soup.get_text()

        summary = get_email_summary(date, sender, subject, text_content)

        email_summaries.append({
            # 'id': msg['id'],
            'date': date,
            'from': sender,
            'subject': subject,
            # 'snippet': snippet,
            # 'text_content': text_content
            'summarty': summary
        })

    return email_summaries


def send_email(service, recipient, subject, body):
    message = EmailMessage()
    message.set_content(body)
    message['To'] = recipient
    message['From'] = 'me'
    message['Subject'] = subject

    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    create_message = {
        'raw': encoded_message
    }

    send_message = service.users().messages().send(userId="me", body=create_message).execute()
    return send_message


def email_manager(args: dict):
    """Main emails control function"""
    client_secret_file = 'agent/gmail_tool/client_secret_file.json'
    # client_secret_file = 'client_secret_file.json' # -- Testing purpose only
    API_SERVICE_NAME = 'gmail'
    API_VERSION = 'v1'
    SCOPES = ['https://mail.google.com/']
    me = 'ayushtanwar1729@gmail.com'

    service = create_service(client_secret_file, API_SERVICE_NAME, API_VERSION, *SCOPES)

    service_type = args.get("type")

    if service_type == "list_recent_emails":
        return list_recent_emails(service, me, max_results=args.get("count"), label_ids=['INBOX'])

    elif service_type == "send_email":
        print (args)
        if not all(key in args for key in ("recipient", "subject", "body")):
            return "[ERROR] Missing required fields for sending email"
        try:
            ai_email_content = write_email(args["body"], args["subject"], args["recipient"])
            print (f"AI Email Content: {ai_email_content}")
            args["body"] = ai_email_content.get("body", "")
            args["subject"] = ai_email_content.get("subject", "")
            args["recipient"] = ai_email_content.get("recipient", "")
        except Exception as e:
            return f"[ERROR] Mitchi failed to write email content: {str(e)}"
        return send_email(service, recipient=args.get("recipient"), subject=args.get("subject"), body=args.get("body"))


# -- Testing purpose only

# if __name__ == "__main__":
#     print ("Gmail Service Module")

#     args =  { "type": "send_email", "to": "ayushtanwar1729@gmail.com", "subject": "Test Subject", "body": "This is a test email body." }

#     print(email_manager(args))