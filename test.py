#!/usr/bin/python


from datetime import timedelta
import sys
import requests
import json
import hmac
import hashlib
import base64
import urllib
from datetime import datetime
from cryptacular.bcrypt import BCRYPTPasswordManager
    
def test_ipbb(nop):
    utc_date = datetime.utcnow()
    tStamp = utc_date-datetime.strptime('1970-01-01 00:00:00','%Y-%m-%d %H:%M:%S'); 
    value = "admin&%s" % int(tStamp.total_seconds()); 
    key = "admin";

    signature = hmac.new(key, msg=value, digestmod=hashlib.sha256).digest() 
    
    encodedSignature = base64.encodestring(signature).replace('\n', '')
    data = {
              "jsonrpc": "2.0",
              "method": "get_ipbb",
              "params": [nop],
              "id":1
            }
    print key
    print value
    print encodedSignature
    
    
    signature = hmac.new(key, msg=value, digestmod=hashlib.sha256).digest() 
    
    encodedSignature = base64.encodestring(signature).replace('\n', '')
    data = {
              "jsonrpc": "2.0",
              "method": "get_ipbb",
              "params": [nop],
              "id":1
            }
    print key
    print value
    print encodedSignature
    
    
    jsondata=json.dumps(data, ensure_ascii=False)        
    headers = {'userid':'admin',
               'signature':encodedSignature,
               'key':int(tStamp.total_seconds())}
               
    #url = "http://192.168.56.5:6543/test"
    url = "http://localhost:6543/pbb"
    rows = requests.post(url, data=jsondata,headers=headers)
    print rows.text
    #datas = json.loads(rows.text)
    #for data in datas:
    #    print data
        
    return True
if __name__ == '__main__':
    print dir(hmac)
    nop = '6110010001002004602005'
    if len(sys.argv)>1:
        nop = sys.argv[1].strip()
    test_ipbb(nop)
    