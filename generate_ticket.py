from io import BytesIO

from PIL import Image, ImageDraw, ImageFont


def generate_ticket(context: dict):
	departure_city = context['departure_city']
	destination_city = context['destination_city']
	date = context['dates']
	quantity_passengers = str(context['quantity_passengers'])

	base = Image.open('ticket/ticket_base.png').convert("RGBA")
	# passenger_ticket = Image.new("RGBA", base.size, (255, 255, 255, 0))
	font = ImageFont.truetype('ticket/19676.ttf', 60)
	pt = ImageDraw.Draw(base)

	pt.text((250, 360), departure_city, font=font, fill=(0, 0, 0, 255))
	pt.text((1293, 360), destination_city, font=font, fill=(0, 0, 0, 255))
	pt.text((372, 635), date, font=font, fill=(0, 0, 0, 255))
	pt.text((1683, 635), quantity_passengers, font=font, fill=(0, 0, 0, 255))

	# response = requests.get(url=f'')
	# avatar_file = BytesIO(response.content)
	# avatar = Image.open(avatar_file)
	#
	# base.paste(avatar)
	temp_file = BytesIO()
	base.save(temp_file, 'png')
	temp_file.seek(0)

	return temp_file


if __name__ == '__main__':
	demonstration = {
		'departure_city': 'Екатеринбург',
		'destination_city': 'Ростов-на-Дону',
		'dates': '2020-12-07',
		'quantity_passengers': '3',
		'tlf_number': '+79282704970'
	}
	generate_ticket(demonstration)
