import logging
from calendar import Calendar
from datetime import datetime, date

import requests
import vk_api
import vk_api.utils
from pony.orm import db_session
from vk_api.bot_longpoll import VkBotLongPoll

import handlers
# from settings import FLIGHT_SCHEDULE
from models import UserState, FlightRequests

try:
	import settings
except ImportError:
	exit('DO copy settings.py.default settings.py and set token!')


def logging_config():
	global bot_logger
	bot_logger = logging.getLogger('BotLog')
	bot_logger.setLevel('INFO')
	formatter = logging.Formatter('%(levelname)s: %(asctime)s - %(message)s', datefmt='%d-%m-%Y %H:%M')
	handler = logging.FileHandler('BotLog.log', encoding='UTF-8', mode='w')
	handler.setFormatter(formatter)
	bot_logger.addHandler(handler)


logging_config()


class ChatBot:
	"""
	Bot for choosing tickets for vk.com
	Use python 3.7
	"""

	def __init__(self, token, group_id):
		"""
		:param token: users secret code
		:param group_id: group id from vk
		"""
		self.token = token
		self.group_id = group_id
		self.vk_api = vk_api.VkApi(token=token)
		self.poller = VkBotLongPoll(self.vk_api, self.group_id)
		self.vk_sess = self.vk_api.get_api()
		self.schedule = []
		self.fly_info = {
			'departure_city': None,
			'destination_city': None,
			'dates': None
		}

	def run(self):
		"""Start bot."""
		for event in self.poller.listen():
			self.event_handling(event)

	@db_session
	def event_handling(self, event):
		if event.type.value is not 'message_new':
			from_id = event.object.from_id
			bot_logger.info(f'{event.type.value} - id:{from_id}')
			return
		message = event.object.message
		user_id = str(message['from_id'])
		message_text = message['text'].lower()

		state = UserState.get(user_id=user_id)

		if state is not None:
			self._continue_scenario(message_text, user_id, state)
		else:
			for intent in settings.INTENTS:
				if any(token in message_text for token in intent['tokens']):
					if intent['answer']:
						self._send_text_message(user_id, intent['answer'])
					else:
						self._start_scenario(intent, user_id)
					break
			else:
				text_to_send = settings.HELP_ANSWER
				self._send_text_message(user_id, text_to_send)

		bot_logger.info(f'{event.type.value} - id:{user_id} - msg:"{message_text}"')

	def _send_step(self, step, user_id, text, context, selector=True):
		if 'text' in step:
			self._send_text_message(user_id, text.format(**context))
		if selector:
			if 'image' in step:
				handler = getattr(handlers, step['image'])
				image = handler(text, context)
				self._send_image_message(user_id, image)

	def _start_scenario(self, intent, user_id):
		scenario_name = intent['scenario']
		scenario = settings.SCENARIOS[scenario_name]
		first_step = scenario['first_step']
		step = scenario['steps'][first_step]
		text = step['text']
		self._send_step(step, user_id, text, context={})
		UserState(user_id=user_id, scenario_name=scenario_name, step_name=first_step, context={})

	def _continue_scenario(self, message_text, user_id, state):
		if message_text in ['/help', '/ticket']:
			for intent in settings.INTENTS:
				if intent['answer']:
					self._send_text_message(user_id, intent['answer'])
				else:
					self._start_scenario(intent, user_id)
			state.delete()

		scenario_name = state.scenario_name
		step = state.step_name
		steps = settings.SCENARIOS[scenario_name]['steps']
		next_step = steps[step]['next_step']

		text_to_send = steps[next_step]['text']
		name_handler = steps[step]['handler']
		handler = getattr(handlers, name_handler)
		param = handler(message_text, state.context)
		if step == 'step4':
			state.context['dates'] = str(self.schedule[param - 1]).replace("(", "").replace(")", "").replace(", ", ".")

		if param:
			if next_step:
				state.step_name = next_step
				if not steps[next_step]['next_step']:
					FlightRequests(
						departure_city=state.context['departure_city'],
						destination_city=state.context['destination_city'],
						dates=state.context['dates'],
						quantity_passengers=str(state.context['quantity_passengers']),
						comment=state.context['comment'],
						tlf_number=state.context['tlf_number']
					)
					state.delete()
			if next_step == 'step3':
				if not self._is_a_flight(state):
					state.delete()
					text_to_send = 'Между указанными городами нет авиасообщения! Заказ билетов остановлен. ' \
					               'Для старта нового бронирования напишите /tickets'

			elif next_step == 'step4':
				self._dispatcher(state)
				for i in range(len(self.schedule)):
					text_to_send += f'\n{i + 1} - ' \
					                f'{str(self.schedule[i]).replace("(", "").replace(")", "").replace(", ", ".")}'
			selector = True
		else:
			if step == 'step7':
				state.delete()
			text_to_send = steps[step]['error_text']
			selector = False
		next_step = steps[next_step]
		self._send_step(next_step, user_id, text_to_send, state.context, selector)

	def _send_text_message(self, from_id, text_message: str):
		"""
		Generate reply message for user.
		:param from_id: message sender id
		:param text_message: text of received message
		:return: None
		"""
		self.vk_sess.messages.send(user_id=from_id,
		                           message=text_message,
		                           random_id=vk_api.utils.get_random_id())

	def _send_image_message(self, from_id, image):
		upload_url = self.vk_sess.photos.getMessagesUploadServer()['upload_url']
		upload_data = requests.post(upload_url, files={'photo': ('image.png', image, 'image/png')}).json()
		image_data = self.vk_sess.photos.saveMessagesPhoto(**upload_data)
		owner_id = image_data[0]['owner_id']
		media_id = image_data[0]['id']
		attachment = f'photo{owner_id}_{media_id}'
		self.vk_sess.messages.send(user_id=from_id,
		                           attachment=attachment,
		                           random_id=vk_api.utils.get_random_id())

	def _is_a_flight(self, state):
		"""
		Checks for air links between cities
		"""
		departure_city = state.context['departure_city']
		destination_city = state.context['destination_city']
		if destination_city in settings.FLIGHT_SCHEDULE[departure_city]:
			return True
		return False

	def _dispatcher(self, state):
		flying_date = str(state.context['dates']).split('-')
		self.schedule = []
		year = int(flying_date[0])
		month = int(flying_date[1])
		day = int(flying_date[2])
		timetable = settings.FLIGHT_SCHEDULE[state.context['departure_city']][state.context['destination_city']]
		if timetable[0] == 'everyday':
			self._daily_flights(year, month, day)
		elif timetable[0] == 'by days of the week':
			self._flights_by_days_of_week(timetable, year, month, day)
		elif timetable[0] == 'by certain numbers':
			self._flights_by_dates(timetable, year, month, day)

	def _daily_flights(self, year, month, day):
		cal = Calendar()
		date_flying = date(year=year, month=month, day=day)
		moth_calendar = cal.itermonthdates(month=month, year=year)
		c = False
		for elem in moth_calendar:
			if elem == date_flying:
				self.schedule.append(str(elem))
				c = True
				if len(self.schedule) == 5:
					return self.schedule
			elif c:
				self.schedule.append(str(elem))
				if len(self.schedule) == 5:
					return self.schedule
		else:
			if month == 12:
				year += 1
				month = 1
			else:
				month += 1
			day = len(self.schedule)
			self._daily_flights(year, month, day)

	def _flights_by_days_of_week(self, timetable, year, month, day):
		cal = Calendar()
		flight_days_of_week = timetable[1]
		moth_calend = cal.itermonthdays4(month=month, year=year)
		for elem in moth_calend:
			day_of_week = list(elem)[3]
			if datetime.now().date() > date(elem[0], elem[1], elem[2]) \
					or date(elem[0], elem[1], elem[2]) < date(year, month, day):
				continue
			if elem[:3] not in self.schedule:
				if day_of_week in flight_days_of_week:
					self.schedule.append(elem[:3])
					if len(self.schedule) == 5:
						return
		else:
			if month == 12:
				year += 1
				month = 1
			else:
				month += 1
			day = len(self.schedule) + 1
			self._flights_by_days_of_week(timetable, year, month, day)

	def _flights_by_dates(self, timetable, year, month, day):
		cal = Calendar()
		flight_days_of_week = timetable[1]
		moth_calend = cal.itermonthdays3(month=month, year=year)
		for elem in moth_calend:
			day_of_week = list(elem)[2]
			if datetime.now().date() > date(elem[0], elem[1], elem[2]) \
					or date(elem[0], elem[1], elem[2]) < date(year, month, day):
				continue
			if elem[:3] not in self.schedule:
				if day_of_week in flight_days_of_week:
					self.schedule.append(elem[:3])
					if len(self.schedule) == 5:
						return
		else:
			if month == 12:
				year += 1
				month = 1
			else:
				month += 1
			day = 1
			self._flights_by_dates(timetable, year, month, day)


if __name__ == '__main__':
	bot = ChatBot(token=settings.TOKEN, group_id=settings.GROUP_ID)
	bot.run()
