from flask import Flask,jsonify
from flask_restful import Api, Resource, reqparse, abort,fields, marshal_with
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash,check_password_hash
from flask_jwt_extended import JWTManager, jwt_required, create_access_token,get_jti,get_jwt, get_jwt_identity, unset_jwt_cookies,unset_access_cookies
from sqlalchemy import or_

from datetime import datetime,timedelta,timezone



app = Flask(__name__)
api = Api(app)
app.config['SQLALCHEMY_DATABASE_URI'] ='sqlite:///database.db'
app.config['SECRET_KEY'] = 'potato'  # Set a secret key for JWT
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=1)



db = SQLAlchemy(app)
jwt = JWTManager(app)


# Callback function to check if a JWT exists in the database blocklist
@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload: dict) -> bool:
    jti = jwt_payload["jti"]
    token = db.session.query(TokenBlocklist.id).filter_by(jti=jti).scalar()

    return token is not None

# Initialize an empty set to store revoked tokens
class TokenBlocklist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    contact_info = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # 'client' or 'company'

class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact_info = db.Column(db.String(100), nullable=False)

class Bus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    operator_info = db.Column(db.String(100), nullable=True)

class Route(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    origin = db.Column(db.String(100), nullable=False)
    destination = db.Column(db.String(100), nullable=False)
    distance = db.Column(db.Integer, nullable=False)
    estimated_time = db.Column(db.Integer, nullable=False)

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bus_id = db.Column(db.Integer, db.ForeignKey('bus.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    route_id = db.Column(db.Integer, db.ForeignKey('route.id'), nullable=False)
    departure_time = db.Column(db.DateTime, nullable=False)
    arrival_time = db.Column(db.DateTime, nullable=False)
    days_of_operation = db.Column(db.String(100), nullable=False)
    total_price = db.Column(db.Integer, nullable=False)


class Seat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedule.id'), nullable=False)
    number = db.Column(db.Integer, nullable=False)
    is_booked = db.Column(db.Boolean, default=False)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedule.id'), nullable=False)
    seat_id = db.Column(db.Integer, db.ForeignKey('seat.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False)  # 'confirmed', 'cancelled', etc.
    departure_time = db.Column(db.DateTime, nullable=False)
    arrival_time = db.Column(db.DateTime, nullable=False)
    total_price = db.Column(db.Integer, nullable=False)
    is_one_way = db.Column(db.Boolean, default=False)


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    method = db.Column(db.String(100), nullable=False)  # 'credit_card', 'paypal', etc.
    status = db.Column(db.String(50), nullable=False)  # 'processed', 'failed', etc.
    transaction_date = db.Column(db.Date, nullable=False)
    # def __repr__(self):
    #     return f"Video(id = {name}, booking_id = {views},likes = {likes})"

with app.app_context():
	db.create_all()

user_fields = {
    'id': fields.Integer,
    'name': fields.String,
    'email': fields.String,
    'contact_info': fields.String,
    'role': fields.String
}



bus_fields = {
    'id': fields.Integer,
    'user_id': fields.Integer,
    'capacity': fields.Integer,
    'operator_info': fields.String
}

route_fields = {
    'id': fields.Integer,
    'origin': fields.String,
    'destination': fields.String,
    'distance': fields.Integer,
    'estimated_time': fields.Integer
}

schedule_fields = {
    'id': fields.Integer,
    'bus_id': fields.Integer,
    'user_id':fields.Integer,
    'route_id': fields.Integer,
    'departure_time': fields.DateTime,
    'arrival_time': fields.DateTime,
    'days_of_operation': fields.String,
    'total_price':fields.Integer,
}
schedule_fields_response = {
    'data': fields.List(fields.Nested({
    'id': fields.Integer,
    'bus_id': fields.Integer,
    'user_id':fields.Integer,
    'route_id': fields.Integer,
    'departure_time': fields.String,
    'arrival_time': fields.String,
    'days_of_operation': fields.String,
    'total_price':fields.Integer,
    
    }))
    }

schedule_route_fields ={
    'data': fields.List(fields.Nested({
        'schedules': fields.Nested(schedule_fields),
        'routes': fields.Nested(route_fields)
    }))
}

seat_fields = {
    'id': fields.Integer,
    'schedule_id': fields.Integer,
    'number': fields.Integer,
    'is_booked': fields.Boolean
}


booking_fields = {
    'id': fields.Integer,
    'user_id': fields.Integer,
    'schedule_id': fields.Integer,
    'seat_id': fields.Integer,
    'status': fields.String,
    'total_price': fields.Integer,
    'is_one_way':fields.Boolean,
    'departure_time': fields.String,
    'arrival_time': fields.String,
}


booking_route_fields = {
    'data': fields.List(fields.Nested({
        'bookings': fields.Nested(booking_fields),
        'routes': fields.Nested(route_fields)
    }))
}

payment_fields = {
    'id': fields.Integer,
    'booking_id': fields.Integer,
    'amount': fields.Float,
    'method': fields.String,
    'status': fields.String,
    'transaction_date': fields.String
}


# Function to add a new journey for a company user
def add_journey_for_company(user_id, route_id, bus_id, departure_time, arrival_time, days_of_operation, bus_capacity,origin,destination,distance,estimated_time,total_price):
    # Check if the user is a company

    user = User.query.get(user_id)
    if user and user.role == 'company':

        # Create a new bus
        new_bus = Bus(id=bus_id, capacity=bus_capacity, user_id=user_id,operator_info="aaa")
        db.session.add(new_bus)
        db.session.commit()

        # Create a new schedule
        new_schedule = Schedule(bus_id=new_bus.id,user_id=user.id, route_id=route_id, departure_time=datetime.strptime(departure_time,"%H:%M"), arrival_time=datetime.strptime(arrival_time,"%H:%M"),total_price=total_price,days_of_operation=days_of_operation)
        print("+++++++++++++++Role+++++++++++++++++++++")
        print(new_schedule.arrival_time)
        print("+++++++++++++++++++++++++++++++++++++++++")
        db.session.add(new_schedule)
        db.session.commit()

        # create new route for scheduale
        new_router = Route(id = route_id , origin = origin,destination= destination,estimated_time=estimated_time,distance=distance)
        db.session.add(new_router)
        db.session.commit()

        # Create seats for the new bus
        for seat_number in range(1, bus_capacity + 1):
            new_seat = Seat(schedule_id=new_schedule.id, number=seat_number)
            db.session.add(new_seat)
        db.session.commit()


        return 'New journey added successfully.',200
    else:
        return 'Unauthorized: User is not a company.',501



def view_all_bookings(user_id):
    if user_id is not None:
        all_bookings = Booking.query.filter_by(user_id = user_id).all()
        return all_bookings
    else:
        all_bookings = Booking.query.all()
        return all_bookings

def view_journeys_by_dates(departure_date, arrival_date):
    # Convert the dates from string to datetime objects
    departure_date = datetime.strptime(departure_date, '%Y-%m-%d %H:%M:%S')
    arrival_date = datetime.strptime(arrival_date, '%Y-%m-%d %H:%M:%S')

    try:
        # Retrieve all journeys that fall within the specified date range
        journeys = Schedule.query.filter(Schedule.departure_time >= departure_date, Schedule.arrival_time <= arrival_date).all()
        return journeys
    except Exception as e:
        return {"error": str(e)}, 500
def schedule_to_dict(schedule):
    return {
        'id': schedule.id,
        'bus_id': schedule.bus_id,
        'user_id':schedule.user_id,
        'route_id': schedule.route_id,
        'departure_time': schedule.departure_time.isoformat(),
        'arrival_time': schedule.arrival_time.isoformat(),
        'days_of_operation': schedule.days_of_operation,
        'total_price':schedule.total_price
}
def view_journeys_by_location(origin, destination):

    print(origin)
    try:
       
        schedules = db.session.query(Schedule).join(Route, Schedule.route_id == Route.id).filter(Route.origin == origin, Route.destination == destination).all()
        # print(route.json())
        schedules = [schedule_to_dict(schedule) for schedule in schedules]
        return schedules
        # return route
    except Exception as e:
        return {"error": str(e)}, 500

# Function to view all journeys for a client user
def view_all_journeys():

    try:
        all_journeys = Schedule.query.all()
        if all_journeys:
            for journey in all_journeys:
                print(journey.id)
        return all_journeys
    except Exception as e:
        return {"error": str(e)}, 500

def view_routes_by_id(ids):
    print(ids)
    routes = Route.query.all()
    result = []
        # Book the seats
    for route in routes:
        if route.id in ids:
            result.append(route)
    # routes = Route.query.filter(Route.id.in_(ids)).all()
            print(result)
    return result
def view_schedules_by_id(ids):
    print(ids)
    schedules = Schedule.query.all()
    result = []
        # Book the seats
    for schedule in schedules:
        if schedule.id in ids:
            result.append(schedule)
    # routes = Route.query.filter(Route.id.in_(ids)).all()
            print(result)
    return result

def view_all_users():
    # Retrieve all journeys
    all_users = User.query.all()
    return all_users
# Function to book a journey for a client user
def book_journey(user_id, schedule_id, seat_numbers, is_one_way):
    # Check if the user is a client
    user = User.query.get(user_id)
    if user and user.role == 'client':
        # Check if the journey exists and has the requested seats available
        schedule = Schedule.query.get(schedule_id)
        total_price=schedule.total_price
        departure_time =schedule.departure_time
        arrival_time = schedule.departure_time
        print(schedule.total_price) 
        if schedule:
            # Check if requested seats are available
            available_seats = Seat.query.filter(Seat.schedule_id == schedule_id, Seat.number.in_(seat_numbers), Seat.is_booked == False).all()
            if len(available_seats) == len(seat_numbers):
                # Book the seats
                for seat in available_seats:
                    seat.is_booked = True
                    # Create a booking record
                    new_booking = Booking(user_id=user_id, schedule_id=schedule_id, seat_id=seat.id, status='Confirmed', total_price = total_price, is_one_way=is_one_way,departure_time=departure_time,arrival_time=arrival_time)  # Set price as needed
                    db.session.add(new_booking)
                db.session.commit()
                return 'Booking successful.'
            else:
                return 'One or more requested seats are not available.'
        else:
            return 'Journey does not exist.'
    else:
        return "Unauthorized: Only clients can book a journey"






class UserResource(Resource):
    @marshal_with(user_fields)
    # @jwt_required()
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('name', type=str, required=True, help="Name of the user is required")
        parser.add_argument('email', type=str, required=True, help="Email of the user is required")
        parser.add_argument('password', type=str, required=True, help="Password of the user is required")
        parser.add_argument('contact_info', type=str, required=True, help="Contact info of the user is required")
        parser.add_argument('role', type=str, required=True, help="Role of the user is required", choices=('client', 'company'))
        args = parser.parse_args()
              # Generate password hash
        hashed_password = generate_password_hash(args['password'])

                # Create a new User instance
        new_user = User(
            name=args['name'],
            email=args['email'],
            password=hashed_password,
            contact_info=args['contact_info'],
            role=args['role']
        )
                # Add the new user to the database
        db.session.add(new_user)
        db.session.commit()
        return "created", 201



class LoginResource(Resource):
    def post(self):
        parser = reqparse.RequestParser(bundle_errors=True)
        parser.add_argument('email', type=str, required=True, help="Email is required")
        parser.add_argument('password', type=str, required=True, help="Password is required")
        args = parser.parse_args()

        user = User.query.filter_by(email=args['email']).first()
        if user and check_password_hash(user.password, args['password']):
            # Generate an access token (JWT)
            
            access_token = create_access_token(identity=user.id,fresh=True)
                        
            return {'access_token': access_token,'name':user.name,'user_id':user.id,'role':user.role}, 200
        else:
            return {'message': 'Invalid credentials'}, 401


class LogoutResource(Resource):
    @jwt_required()
    def post(self):

        jti = get_jwt()["jti"]
        now = datetime.now(timezone.utc)
        db.session.add(TokenBlocklist(jti=jti, created_at=now))
        db.session.commit()
        response = jsonify({'message': str(get_jwt_identity)})
        unset_jwt_cookies(response)
        return response

# Resource to add a new journey for a company user
class AddJourney(Resource):
    @marshal_with(schedule_fields)
    @jwt_required()  # Requires a valid token
    def post(self):

        user_id = get_jwt_identity()  # Get user ID from token
        print(user_id)
        parser = reqparse.RequestParser(bundle_errors=True)
        parser.add_argument('route_id', type=int, required=True, help="Route ID is required")
        parser.add_argument('bus_id', type=str, required=True, help="Bus id is required")
        parser.add_argument('departure_time', type=str, required=True, help="Departure time is  required")
        parser.add_argument('arrival_time', type=str, required=True, help="Arrival time is required")
        parser.add_argument('days_of_operation', type=str, required=True, help="Days of operation are required")
        parser.add_argument('bus_capacity', type=int, required=True, help="Bus capacity is required")
        parser.add_argument('origin', type=str, required=True, help="origin is required")
        parser.add_argument('destination', type=str, required=True, help="destination is required")
        parser.add_argument('distance', type=int, required=True, help="distance is required")
        parser.add_argument('estimated_time', type=int, required=True, help="estimated_time is required")
        parser.add_argument('total_price', type=int, required=True, help="total_price is required")

        args = parser.parse_args()
        print(args['arrival_time'])
        result = add_journey_for_company(user_id, args['route_id'], args['bus_id'], args['departure_time'], args['arrival_time'], args['days_of_operation'], args['bus_capacity'],args['origin'],args['destination'],args['distance'],args['estimated_time'],args['total_price'])

        return result

class ViewBookings(Resource):
    @marshal_with(booking_fields)
    @jwt_required()
    def get(self):
            user_id = get_jwt_identity() 
            bookings = Booking.query.filter_by(user_id = user_id).all()
            return bookings

class ViewBookingsWithRoute(Resource):
    @marshal_with(booking_route_fields)
    @jwt_required()
    def get(self):
        try:

            user_id = get_jwt_identity() 
            data = []
            bookings = Booking.query.filter_by(user_id = user_id).all()

            for booking in bookings:
                schedule = Schedule.query.filter_by(id=booking.schedule_id).first()
                if schedule:
                    route = Route.query.filter_by(id=schedule.route_id).first()
                    if route:
                        data.append({"bookings": booking, "routes": route})
                    else:
                        print("no_route")
                else: 
                    print("no_sched")
            return {"data": data}, 200
        except Exception as e:
            print(f"An error occurred: {e}")

class ViewBookingsWithRouteCompany(Resource):
    @marshal_with(booking_route_fields)
    @jwt_required()
    def get(self):
        try:
            user_id = get_jwt_identity() 
            data = []
            bookings = []

            company_scheds = Schedule.query.filter_by(user_id=user_id).all()


            for sched in company_scheds:
                booking = Booking.query.filter_by(schedule_id = sched.id).first()
                if booking:
                    print(booking.schedule_id)
                    bookings.append(booking)


            for booking in bookings:
                schedule = Schedule.query.filter_by(id=booking.schedule_id).first()
                if schedule:
                    route = Route.query.filter_by(id=schedule.route_id).first()
                    if route:
                        data.append({"bookings": booking, "routes": route})
                    else:
                        print("no_route")
                else: 
                    print("no_sched")
            return {"data": data}, 200
        except Exception as e:
            print(f"An error occurred: {e}")

class ViewRoutes(Resource):
    @marshal_with(route_fields)
    @jwt_required()
    def get(self):
        try:
            routes = Route.query.all()
            return routes
        except Exception as e:
            print(f"An error occurred: {e}")

class ViewRoutesById(Resource):
    @marshal_with(route_fields)
    @jwt_required()
    def get(self):
        try:
            parser = reqparse.RequestParser()
            parser.add_argument('ids', type=list, location='json', required=True, help="List of route ids is required")
            args = parser.parse_args()
            ids = args["ids"]
            routes = Route.query.all()
            result = []
            for route in routes:
                if route.id in ids:
                    result.append(route)
                    print(result)
            return result
        except Exception as e:
            print(f"An error occurred: {e}")


# Resource to view all journeys for a client user
class ViewJourneys(Resource):
    @marshal_with(schedule_fields_response)
    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()  # Get user ID from token
        journeys = Schedule.query.filter_by(user_id=user_id)
        # journeys = view_all_journeys()
        return {"data": journeys}
    
def to_dict(instance):
    return {c.key: getattr(instance, c.key) for c in db.inspect(instance).mapper.column_attrs}

class ViewJourneysWithRoute(Resource):
    @jwt_required()
    def get(self):
        try:
            data = []
            schedules = Schedule.query.all()
            schedules = [schedule_to_dict(schedule) for schedule in schedules]

            for schedule in schedules:
                second_item = list(schedule.items())[3]
                print(second_item)
                if schedule:
                    route = Route.query.filter_by(id=second_item[1]).first()
                    if route:
                        data.append({"schedules": schedule, "routes": to_dict(route)})

            return {"data": data}, 200
        except Exception as e:
            print(f"An error occurred: {e}")

class ViewJourneysWithRouteByUser(Resource):
    @jwt_required()
    def get(self):

        user_id = get_jwt_identity()  # Get user ID from token

        try:
            data = []
            schedules = Schedule.query.filter_by(user_id=user_id).all()
            schedules = [schedule_to_dict(schedule) for schedule in schedules]

            for schedule in schedules:
                second_item = list(schedule.items())[3]
                print(second_item)
                if schedule:
                    route = Route.query.filter_by(id=second_item[1]).first()
                    print(route)
                    if route:
                        data.append({"schedules": schedule, "routes": to_dict(route)})

            return {"data": data}, 200
        except Exception as e:
            print(f"An error occurred: {e}")
class ViewJourneysByDate(Resource):
    @marshal_with(schedule_fields_response)
    @jwt_required()
    def get(self):
        # Create a parser for the incoming arguments
        parser = reqparse.RequestParser()

        # Add the departure and arrival date arguments
        parser.add_argument('departure_date', type=str, help='Date of departure')
        parser.add_argument('arrival_date', type=str, help='Date of arrival')

        # Parse the arguments
        args = parser.parse_args()

        # Get the departure and arrival dates from the arguments
        departure_date = args.get('departure_date')
        arrival_date = args.get('arrival_date')

        # Call the function to view journeys based on the dates
        journeys = view_journeys_by_dates(departure_date, arrival_date)

        return journeys    
    
class ViewJourneysByLocation(Resource):
    # @marshal_with(schedule_fields_response)
    @jwt_required()
    def get(self):
        # Create a parser for the incoming arguments
        parser = reqparse.RequestParser()

        # Add the departure and arrival date arguments
        parser.add_argument('origin', type=str, help='origin')
        parser.add_argument('destination', type=str, help='destination')

        # Parse the arguments
        args = parser.parse_args()

        # Get the departure and arrival dates from the arguments
        origin = args.get('origin')
        destination = args.get('destination')

        # Call the function to view journeys based on the dates
        journeys = view_journeys_by_location(origin, destination)

        return journeys    
class ViewUsers(Resource):
    @marshal_with(user_fields)
    @jwt_required()
    def get(self):
        users = view_all_users()
        return users


class ViewSeats(Resource):
    @marshal_with(seat_fields)
    @jwt_required()
    def get(self):

        parser = reqparse.RequestParser()

        # Add the departure and arrival date arguments
        parser.add_argument('sched_id', type=int, help='sched_id')

        # Parse the arguments
        args = parser.parse_args()

        # Get the departure and arrival dates from the arguments
        sched_id = args.get('sched_id')
        # Retrieve all seats
        seats = Seat.query.filter_by(schedule_id = sched_id).all()

        # If there are no seats, return an error message
        if not seats:
            abort(404, message="No seats found")

        return seats
    
class ViewBus(Resource):
    @marshal_with(bus_fields)
    @jwt_required()
    def get(self, bus_id):
        # Retrieve the bus by its id
        bus = Bus.query.get(bus_id)

        # If the bus does not exist, return an error message
        if not bus:
            abort(404, message="Bus with id {} doesn't exist".format(bus_id))

        return bus
# Resource to book a journey for a client user
class BookJourney(Resource):
    @jwt_required()
    def post(self):
        user_id = get_jwt_identity()  # Get user ID from token
        parser = reqparse.RequestParser()
        parser.add_argument('schedule_id', type=int, required=True, help="Schedule ID is required")
        parser.add_argument('seat_numbers', type=list, location='json', required=True, help="List of seat numbers is required")
        parser.add_argument('is_one_way', type=int, required=True, help="is_one_way is required")
        args = parser.parse_args()

        result = book_journey(user_id, args['schedule_id'], args['seat_numbers'], args['is_one_way'])
        if not result.startswith('Unauthorized') and not result.startswith('One or more requested seats are not available'):
            return {'message': result}, 200
        elif result.startswith('One or more requested seats are not available'):
            abort(409, message=result)
        else:
            abort(401, message=result)

class DeleteBooking(Resource):
    @jwt_required()
    def delete(self):
        parser = reqparse.RequestParser()
        parser.add_argument('booking_id', type=int, required=True, help="Booking ID is required")
        args = parser.parse_args()

        booking = Booking.query.get(args['booking_id'])
        if booking:
            # Get the seat associated with the booking
            seat = Seat.query.get(booking.seat_id)
            if seat:
                # Set the seat to not booked
                seat.is_booked = False
                db.session.add(seat)

            # Delete the booking
            db.session.delete(booking)
            db.session.commit()
            return {'message': 'Booking deleted and seat status updated successfully'}, 200
        else:
            abort(404, message="Booking not found")


class DeleteJourney(Resource):
    @jwt_required()
    def delete(self):
        parser = reqparse.RequestParser()
        parser.add_argument('schedule_id', type=int, required=True, help="Schedule ID is required")
        args = parser.parse_args()
        print(args['schedule_id'])
        schedule = Schedule.query.get(args['schedule_id'])
        if schedule:
            # Get the bus associated with the schedule
            bus = Bus.query.get(schedule.bus_id)
            
            # Get all bookings associated with this schedule
            bookings = Booking.query.filter_by(schedule_id=schedule.id).all()
            for booking in bookings:
                # Get the seat associated with the booking
                seat = Seat.query.get(booking.seat_id)
                if seat:
                    # Delete the seat
                    db.session.delete(seat)

                # Delete the booking
                db.session.delete(booking)

            # Delete the bus
            if bus:
                db.session.delete(bus)

            # Delete the schedule
            db.session.delete(schedule)
            db.session.commit()
            return {'message': 'Journey and all associated bookings, seats, and bus deleted successfully'}, 200
        else:
            abort(404, message="Journey not found")


api.add_resource(AddJourney, '/add_journey')
api.add_resource(ViewJourneys, '/view_journeys')
api.add_resource(ViewJourneysWithRoute, '/view_journeys_route')
api.add_resource(ViewJourneysWithRouteByUser, '/view_journeys_route_user')
api.add_resource(ViewJourneysByDate, '/view_journeys_by_date')
api.add_resource(ViewJourneysByLocation, '/view_journeys_by_location')
api.add_resource(BookJourney, '/book_journey')
api.add_resource(DeleteJourney, '/deletejourney')

api.add_resource(ViewBookings, '/view_bookings')
api.add_resource(ViewBookingsWithRoute, '/view_bookings_route')
api.add_resource(ViewBookingsWithRouteCompany, '/view_bookings_route_company')
api.add_resource(ViewRoutes, '/view_routes')
api.add_resource(ViewRoutesById, '/view_routes_by_id')
api.add_resource(ViewBus, '/view_bus_by_id/<int:bus_id>')
api.add_resource(ViewSeats, '/view_seats')
api.add_resource(DeleteBooking, '/deletebooking')

api.add_resource(ViewUsers, '/view_users')
api.add_resource(UserResource, '/add_user')    
api.add_resource(LoginResource, '/login')
api.add_resource(LogoutResource, '/logout')


if __name__ == "__main__":
    app.run(debug=True)
