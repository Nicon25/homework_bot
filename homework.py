import logging
import os

import requests

import telegram
import time

from dotenv import load_dotenv

import sys

from http import HTTPStatus

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

# logging.basicConfig(
#     level=logging.DEBUG,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     stream=sys.stdout)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность переменных окружения."""
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        return True


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.debug(
            f'Отправлено сообщение в чат {TELEGRAM_CHAT_ID}: {message}'
        )
    except telegram.TelegramError as error:
        logger.error(f'Ошибка Telegram: {error}')
    except Exception:
        logger.error('Ошибка отправки сообщения в чат')


def get_api_answer(timestamp):
    """Делает запрос к эндпоинту API-сервиса.
    В качестве параметра функция получает временную метку.
    В случае успешного запроса должна вернуть ответ API,
    преобразовав его из формата JSON к типам данных Python.
    """
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != HTTPStatus.OK:
            logging.error(f'Ошибка {response.status_code}')
            raise Exception(f'Ошибка {response.status_code}')
    except Exception as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')
        raise Exception(f'Ошибка при запросе к основному API: {error}')
    try:
        return(response.json())
    except ValueError:
        logger.error('Ошибка парсинга ответа из формата json')
        raise ValueError('Ошибка парсинга ответа из формата json')


def check_response(response):
    """Проверяет ответ API на корректность.
    Если ответ API соответствует ожиданиям, то функция должна вернуть
    список домашних работ, доступный в ответе API по ключу 'homeworks'
    """
    if not isinstance(response, dict):
        raise TypeError('Тип ответа API отличен от словаря')
    if not isinstance(response.get('homeworks'), list):
        raise TypeError('В ответе API данные приходят не в виде списка.')
    try:
        list_homeworks = response['homeworks']
    except KeyError:
        logger.error('Ошибка словаря по ключу homeworks')
        raise KeyError('Ошибка словаря по ключу homeworks')
    try:
        homework = list_homeworks[0]
    except IndexError:
        logger.error('Список домашних работ пуст')
        raise IndexError('Список домашних работ пуст')
    return homework


def parse_status(homework):
    """Извлекает статус домашней работы.
    В качестве параметра функция получает один элемент из списка домашних
    работ. В случае успеха, функция возвращает подготовленную для отправки в
    Telegram строку, содержащую один из вердиктов словаря HOMEWORK_VERDICTS.
    """
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ "homework_name" в ответе API')
    if 'status' not in homework:
        raise Exception('Отсутствует ключ "status" в ответе API')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_VERDICTS:
        raise Exception(f'Неизвестный статус работы: {homework_status}')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствуют переменные окружения')
        sys.exit('Отсутствуют переменные окружения')
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
            logger.error(f'Сбой в работе программы: {error}')
            message = f'Сбой в работе программы: {error}'
            if message not in error_message and message is True:
                error_message = message
                send_message(bot, message)
                logger.error(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
