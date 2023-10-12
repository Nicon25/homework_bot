import logging
import os
import sys
import time
from http import HTTPStatus
from json import JSONDecodeError

import requests
import telegram
from dotenv import load_dotenv

from exceptions import HTTPRequestError, ParseStatusError

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Work has been reviewed: the reviewer liked everything. Hooray!',
    'reviewing': 'The work is under review by the reviewer.',
    'rejected': 'Work has been reviewed: the reviewer has some comments.'
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens():
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        return True


def send_message(bot, message):
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.debug(
            f'A message has been sent in the chat {TELEGRAM_CHAT_ID}: {message}'
        )
    except telegram.TelegramError as error:
        logger.error(f'Telegram error: {error}')
    except Exception:
        logger.error('Error sending a message in the chat')


def get_api_answer(timestamp):
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != HTTPStatus.OK:
            raise HTTPRequestError(response)
    except Exception as error:
        raise Exception(f'Error when making a request to the main API: {error}')
    try:
        return(response.json())
    except JSONDecodeError as error:
        raise error('Error parsing the response from the JSON format')


def check_response(response):
    if not isinstance(response, dict):
        raise TypeError('The API response type is different from a dictionary')
    if not isinstance(response.get('homeworks'), list):
        raise TypeError('The API response data is not in the form of a list.')
    try:
        list_homeworks = response['homeworks']
    except KeyError:
        raise KeyError('Dictionary error for the key 'homeworks'')
    try:
        homework = list_homeworks[0]
    except IndexError:
        raise IndexError('The list of homework assignments is empty')
    return homework


def parse_status(homework):
    if 'homework_name' not in homework:
        raise KeyError('The 'homework_name' key is missing in the API response')
    if 'status' not in homework:
        raise KeyError('The 'status' key is missing in the API response')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_VERDICTS:
        raise ParseStatusError(homework_status)
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'The status of the work "{homework_name}" review has changed. {verdict}'


def main():
    if not check_tokens():
        logger.critical('Environment variables are missing')
        sys.exit('Environment variables are missing')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    error_message = ''
    status = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            check = check_response(response)
            timestamp = response.get('current_date', timestamp)
            if check:
                new_status = parse_status(check)
                if new_status != status:
                    send_message(bot, new_status)
                    status = new_status
        except Exception as error:
            message = f'Program malfunction: {error}'
            if message not in error_message and message:
                error_message = message
                send_message(bot, message)
                logger.error(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
