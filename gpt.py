import json
import logging

import requests
from config import *
from database import *
import sqlite3
import time
import os



def create_new_token():
    metadata_url = "http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token"
    headers = {"Metadata-Flavor": "Google"}

    token_dir=os.path.dirname('token.json')
    if not os.path.exists(token_dir):
        os.makedirs(token_dir)
    try:
        response = requests.get(metadata_url, headers=headers)
        if response.status_code == 200:
            token_data=response.json()
            token_data['expires_at']=time.time()+token_data['expires_in']
            with open('token.json','w') as token_file:
                json.dump(token_data, token_file)
        else:
            logging.error(f'ошибка. Статус кода: {response.status_code}')
    except Exception as e:
        logging.error(e)


def get_creds():
    try:
        with open('token.json','r') as f:
            d=json.load(f)
            expiriation=d['expires_at']
        if expiriation<time.time():
            create_new_token()
    except:
        create_new_token()

    with open('token.json','r') as f:
        d=json.load(f)
        token=d['access_token']
    return token


def gpt_answer_content(user_id):
    connection = sqlite3.connect('speech_kit.db')
    cur = connection.cursor()
    query = f'SELECT gpt_answer FROM gpt_answer WHERE user_id = {user_id}'
    results = cur.execute(query).fetchone()
    if results:
        return results[0]
    else:
        return

def text_to_speech(text: str):
    iam_token = get_creds()
    folder_id = FOLDER_ID

    # Аутентификация через IAM-токен
    headers = {
        'Authorization': f'Bearer {iam_token}',
    }
    data = {
        'text': text,  # текст, который нужно преобразовать в голосовое сообщение
        'lang': 'ru-RU',  # язык текста - русский
        'voice': 'zahar',  # голос Филиппа
        'folderId': folder_id,
    }
    # Выполняем запрос
    response = requests.post('https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize',
                             headers=headers, data=data)

    if response.status_code == 200:
        return True, response.content  # Возвращаем голосовое сообщение
    else:
        return False, "При запросе в SpeechKit возникла ошибка"


def speech_to_text(data):
    IAM_TOKEN=get_creds()


    # Указываем параметры запроса
    params = "&".join([
        "topic=general",  # используем основную версию модели
        f"folderId={FOLDER_ID}",
        "lang=ru-RU"  # распознаём голосовое сообщение на русском языке
    ])

    # Аутентификация через IAM-токен
    headers = {
        'Authorization': f'Bearer {IAM_TOKEN}',
    }

    # Выполняем запрос
    response = requests.post(
        f"https://stt.api.cloud.yandex.net/speech/v1/stt:recognize?{params}",
        headers=headers,
        data=data
    )

    # Читаем json в словарь
    decoded_data = response.json()
    # Проверяем, не произошла ли ошибка при запросе
    if decoded_data.get("error_code") is None:
        return True, decoded_data.get("result")  # Возвращаем статус и текст из аудио
    else:
        return False, "При запросе в SpeechKit возникла ошибка"


def count_tokens_in_dialogue(messages: list)->int:
    IAM_TOKEN=get_creds()

    url = 'https://llm.api.cloud.yandex.net/foundationModels/v1/tokenizeCompletion'
    headers = {
        'Authorization': f'Bearer {IAM_TOKEN}',
        'Content-Type': 'application/json'
    }

    data = {
        "modelUri": f"gpt://{FOLDER_ID}/{GPT_MODEL}/latest",
        "completionOptions": {
            "stream": False,
            "temperature": 0.6,
            "maxTokens": 100
        },
       "messages": []
    }
    for row in messages:
        data["messages"].append(
            {
                "role": row["role"],
                "text": row["text"]
            }
        )


    response=requests.post(url, json=data, headers=headers)
    return len(requests.post(url, json=data, headers=headers).json()['tokens'])#(response.json()['tokens'])


def ask_gpt(text,user_id):
    IAM_TOKEN=get_creds()
    url = f"https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        'Authorization': f'Bearer {IAM_TOKEN}',
        'Content-Type': 'application/json'
    }
    data = {
        "modelUri": f"gpt://{FOLDER_ID}/{GPT_MODEL}/latest",
        "completionOptions": {
            "stream": False,
            "temperature": 0.6,
            "maxTokens": 300
        },
        "messages": [
            {"role": "system", "text": f"Ты бот помощник.Отвечай на вопрос не объясняя ответ. {gpt_answer_content(user_id)}"},
            {"role": "user", "text": f"{text}"},
            {"role": "assistant", "text": f"{gpt_answer_content(user_id)}"}

        ]
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 200:
            logging.debug(f"Response {response.json()} Status code:{response.status_code} Message {response.text}")
            result = f"Status code {response.status_code}. Подробности см. в журнале."
            return result
        result = response.json()['result']['alternatives'][0]['message']['text']
        logging.info(f"Request: {response.request.url}\n"
                     f"Response: {response.status_code}\n"
                     f"Response Body: {response.text}\n"
                     f"Processed Result: {result}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        result = "Произошла непредвиденная ошибка. Подробности см. в журнале."

    return result


