from pony.orm import Database, Required, Json

from settings import DB_CONFIG

db = Database()
db.bind(**DB_CONFIG)


class UserState(db.Entity):
	"""User state in scenario"""
	user_id = Required(str, unique=True)
	scenario_name = Required(str)
	step_name = Required(str)
	context = Required(Json)


class FlightRequests(db.Entity):
	departure_city = Required(str)
	destination_city = Required(str)
	dates = Required(str)
	quantity_passengers = Required(str)
	comment = Required(str)
	tlf_number = Required(str)


db.generate_mapping(create_tables=True)
