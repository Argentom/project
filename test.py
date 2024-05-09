import requests
import time


def check_time():
    metadata_url = "http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token"
    headers = {"Metadata-Flavor": "Google"}
    response = requests.get(metadata_url, headers=headers)
    token_data = response.json()
    expires_at = time.time() + token_data['expires_in']
    print(time.time())
    print(token_data['expires_in'])
    if expires_at<token_data['expires_in']:
        create_new_token()
    else: print('Время еще не прошло')
def create_new_token():
    """Создание нового токена"""
    metadata_url = "http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token"
    headers = {"Metadata-Flavor": "Google"}
    response = requests.get(metadata_url, headers=headers)
    token_data=response.json()
    token=token_data['access_token']
    print(token)
    return token

print(check_time())


