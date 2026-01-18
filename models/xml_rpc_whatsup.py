import json
import xmlrpc.client
import sys
import requests
import smtplib
#l_ip="whatsapp.qimamhd.com"
l_ip="93.127.202.52"
l_port="21465"
l_session="45a60ba3-fbec-4d1e-9fe7-66f0048d5344"
l_secrit="THISISMYSECURETOKEN"
#l_mobile="120363168527874128"
l_mobile="+966500732229"
l_message="تجربة رسالة من الواتس الكود البرمجي "
l_token="$2b$10$bqfyyXxkqcJY6XZUfeHOZeNwaKrzdANEj7Ei6Hb1hkDnbtiEQoU2."
# Send a message to phone
def send_whatsapp(p_ip , p_port ,p_mobile,p_message):
    url = "http://"+p_ip+":"+p_port+"/api/" + l_session +"/send-message"#
    print(url)
    print('Bearer {' + l_token +'}')
    payload = json.dumps({"phone": p_mobile,"message": p_message})
    headers = {
    "Authorization": f'Bearer {"%s"}' %l_token,
    'Content-Type': 'application/json',  # Adjust content type as needed
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    print("\n\n\n\n the response value is :", response.status_code)