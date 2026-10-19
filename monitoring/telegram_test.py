"""Send only the owner's authorized sample; secrets never printed or persisted."""
import argparse
import json
import os
import getpass
import secrets
import re
import ssl
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler

def safe_error(exc, stage):
    """Never echo API bodies, exception text, request URLs or credentials."""
    if isinstance(exc, HTTPError):
        detail = {
            400: 'Telegram rejected the request parameters.',
            401: 'Telegram rejected authentication. Use the latest complete bot token.',
            403: 'Telegram denied access. Check whether the bot is blocked in your chat.',
            404: 'Telegram could not find the API endpoint. Check the complete token.',
            409: 'Telegram reports a polling conflict, possibly an existing webhook or another bot process.',
            429: 'Telegram rate limit reached. Wait before retrying.'
        }.get(exc.code, 'Telegram or the network gateway returned an HTTP error.')
        detail = 'HTTP ' + str(exc.code) + ': ' + detail
    elif isinstance(exc, URLError):
        if isinstance(exc.reason, ssl.SSLCertVerificationError):
            detail = 'TLS certificate verification failed. Do not disable certificate checks.'
        else:
            detail = 'Network connection failed (DNS, proxy, firewall or connection timeout).'
    elif isinstance(exc, (TimeoutError, ConnectionError)):
        detail = 'Network timeout or connection failure.'
    elif isinstance(exc, json.JSONDecodeError):
        detail = 'Received an unexpected non-JSON response, possibly from a network gateway.'
    else:
        detail = 'Unexpected local/API response error (' + type(exc).__name__ + ').'
    delivery = ('Delivery is uncertain; check Telegram before retrying.'
                if stage == 'sendMessage' else 'No sample message was sent.')
    return 'Step: ' + stage + '. ' + detail + ' ' + delivery

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--send-test',action='store_true')
    parser.add_argument('--pair-test',action='store_true')
    args=parser.parse_args()
    token=os.environ.get('AEGIS_TELEGRAM_BOT_TOKEN','').strip()
    chat=os.environ.get('AEGIS_TELEGRAM_CHAT_ID','').strip()
    if args.pair_test:
        token=getpass.getpass('Enter the replacement Telegram bot token (hidden, not saved): ').strip()
    if not token or (not chat and not args.pair_test):
        print(json.dumps({'status':'NOT_CONFIGURED','token_present':bool(token),'destination_present':bool(chat),'sent':False}))
        return 2
    if not re.fullmatch(r'[0-9]+:[A-Za-z0-9_-]{20,}', token):
        print('Token format is incomplete or contains extra text. Copy only the full latest token, including both sides of the colon. Nothing sent.')
        return 2
    if not args.send_test and not args.pair_test:
        print(json.dumps({'status':'CONFIGURED_NOT_VERIFIED','sent':False}))
        return 0
    if not args.pair_test and not chat.isdigit():
        print('Only an explicitly configured positive private chat ID is accepted. Nothing sent.')
        return 2
    opener=build_opener(NoRedirect())
    stage='setup'
    def call(method,body):
        nonlocal stage
        stage=method
        request=Request('https://api.telegram.org/bot'+token+'/'+method,
          data=json.dumps(body).encode(),headers={'Content-Type':'application/json'},method='POST')
        with opener.open(request,timeout=20) as response:
            result=json.load(response)
        if result.get('ok') is not True:
            raise ValueError('API rejected request')
        return result['result']
    try:
        identity=call('getMe',{})
        if not identity.get('is_bot') or (os.environ.get('AEGIS_TELEGRAM_BOT_USERNAME') and identity.get('username','').lower()!=os.environ['AEGIS_TELEGRAM_BOT_USERNAME'].lower()):
            print('Bot identity mismatch. Nothing sent.')
            return 2
        if args.pair_test:
            challenge='AEGIS-PAIR-'+secrets.token_hex(8)
            print('Send this exact message to @'+identity['username']+' in your PRIVATE Telegram chat:')
            print(challenge)
            input('After sending it, press Enter here: ')
            updates=call('getUpdates',{'limit':100,'timeout':0})
            destinations={str(u['message']['chat']['id']) for u in updates
              if u.get('message',{}).get('text')==challenge
              and u['message'].get('chat',{}).get('type')=='private'}
            if len(destinations)!=1:
                print('Pairing message not uniquely found. Nothing sent. Existing webhooks are not changed.')
                return 2
            chat=destinations.pop()
        destination=call('getChat',{'chat_id':chat})
        if destination.get('type')!='private' or str(destination.get('id'))!=chat:
            print('Private destination mismatch. Nothing sent.')
            return 2
        result=call('sendMessage',{'chat_id':chat,'text':
          'AEGIS TEST — Notification connection check. This is a sample, not a buy or sell recommendation. No trade has been placed. Future proposals require your review and manual submission.'})
        print(json.dumps({'status':'TELEGRAM_ACCEPTED','message_id':result['message_id'],'sent':True,
                         'note':'API acceptance does not prove a phone notification was seen.'}))
        if args.pair_test:
            print('One-time test completed. Token was not saved; ongoing notifications are not yet configured.')
        return 0
    except Exception as exc:
        # urllib exception text may contain the token-bearing request URL.
        print(safe_error(exc,stage))
        return 1

if __name__=='__main__':
    raise SystemExit(main())
