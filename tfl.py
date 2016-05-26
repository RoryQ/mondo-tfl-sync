import requests
from lxml import html
from os import environ

config = {}
for key in ('TFL_USERNAME', 'TFL_PASSWORD'):
    config[key] = environ[key]

login_post = "https://account.tfl.gov.uk/Login"
login_url = "http://contactless.tfl.gov.uk/"
mycards_url = "https://contactless.tfl.gov.uk/MyCards"

def login():
    session_requests = requests.session()

    result = session_requests.get(login_url)

    tree = html.fromstring(result.text)
    auth_token = tree.xpath("//input[@name='AppId']/@value")[0]

    payload = {
        "UserName" : config['TFL_USERNAME'],
        "Password" : config['TFL_PASSWORD'],
        "AppId" : auth_token
    }

    # login
    result = session_requests.post(login_post, data = payload, headers = dict(referer = login_url))

    result = session_requests.get(mycards_url, headers = dict(referer = mycards_url))
    tree = html.fromstring(result.content)
    x = '//div[@data-pageobject="mycards-contactless-container" and .//span[@class="view-card-nickname" and contains(.,"Mondo")]]'

    mondo_card = tree.xpath('//a[@data-pageobject="mycards-card-cardlink" and .//span[@class="view-card-nickname" and contains(.,"Mondo")]]/@href')[0]
    print(mondo_card)

if __name__ == '__main__':
    login()