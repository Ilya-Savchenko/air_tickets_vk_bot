import re
from datetime import datetime

from generate_ticket import generate_ticket
from settings import CITIES

re_moscow = re.compile(r'[Мм]оскв\w{,2}')
re_piter = re.compile(r'([Сс]анкт|[Пп][еи]тер\w{,5})')
re_rostov = re.compile(r'\w{,2}-{,1}([Рр]остов|[Дд]он\w{,2})')
re_vladivostok = re.compile(r'[Вв]лади\w{,7}')
re_ekb = re.compile(r'([Ее]катеринб\w{,5}|[Ее]кб)')
re_tlf_num = re.compile(r'\+7\d{10}')

cities = {
	re_moscow: 'Москва',
	re_piter: 'Санкт-Петербург',
	re_rostov: 'Ростов-на-Дону',
	re_vladivostok: 'Владивосток',
	re_ekb: 'Екатеринбург'
}

for i in range(len(CITIES)):
	CITIES[i - 1] = CITIES[i - 1].upper()


def handler_departure_city(city: str, context):
	for elem in cities:
		town = elem.match(city)
		if town:
			city = cities[elem]
			context['departure_city'] = city
			return city
	return False


def handler_destination_city(city: str, context):
	for elem in cities:
		town = elem.match(city)
		if town:
			city = cities[elem]
			context['destination_city'] = city
			return city
	return False


def handler_dates(dates, context):
	try:
		dates = datetime.strptime(dates, '%d.%m.%Y')
	except ValueError:
		return False
	else:
		timedelta = (dates - datetime.now()).days
		if timedelta >= 0:
			context['dates'] = str(dates.date())
			return dates.date()
		return False


def handler_flight_selection(number, context):
	if 0 < int(number) < 6:
		return int(number)
	return False


def handler_quantity_passengers(number, context):
	if 0 < int(number) < 6:
		context['quantity_passengers'] = int(number)
		return int(number)
	return False


def handler_comment(comment, context):
	context['comment'] = comment
	return comment


def handler_answer(answer, context):
	if answer.lower() == 'да':
		return True
	return False


def handler_telephone_number(number, context):
	tlf = re_tlf_num.match(number)
	if tlf:
		context['tlf_number'] = number
		return True
	return False


def handler_generate_ticket(text, context):
	return generate_ticket(context)
