import unittest
from unittest.mock import patch, Mock, ANY

from pony.orm import db_session, rollback

from chatbot import ChatBot

def isolate_db(func):
    def wrapper(*args, **kwargs):
        with db_session:
            func(*args, **kwargs)
            rollback()
    return wrapper

class UserState:
    """User state in scenario"""

    def __init__(self, scenario_name, step_name, context=None):
        self.scenario_name = scenario_name
        self.step_name = step_name
        self.context = context or {}

class TestChatBot(unittest.TestCase):

    def test_create_reply_message(self):
        FROM_ID = 1
        TEXT = 'hi'
        SENDER = 'Petya'
        send_mock = Mock()
        with patch('chatbot.vk_api.VkApi'):
            with patch('chatbot.VkBotLongPoll'):
                chat_bot = ChatBot('', '')
                chat_bot.vk_sess = Mock()
                chat_bot.vk_sess.users.get = Mock(return_value=[{'first_name': SENDER}])
                chat_bot.vk_sess.messages.send = send_mock

                chat_bot._send_text_message(FROM_ID, TEXT)

        send_mock.assert_called_once_with(user_id=FROM_ID,
                                          message=TEXT,
                                          random_id=ANY)

    def test_dispatcher(self):
        CONTEXT = {'departure_city':'Ростов-на-Дону',
                   'destination_city' : 'Екатеринбург',
                   'dates':'2020-12-21'}
        USER_STATE = UserState(scenario_name='search_ticket',
                                   step_name='step1',
                                   context=CONTEXT)
        SHEDULE = [(2020, 12, 21), (2021, 1, 1), (2021, 1, 11), (2021, 1, 21), (2021, 2, 1)]
        with patch('chatbot.vk_api.VkApi'):
            with patch('chatbot.VkBotLongPoll'):
                chat_bot = ChatBot('', '')
                chat_bot._dispatcher(USER_STATE)

        self.assertEqual(chat_bot.schedule, SHEDULE)
