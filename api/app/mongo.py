import pymongo
from bson.objectid import ObjectId
import app.settings as settings
import app.models as models
import app.web10records as records
import app.exceptions as exceptions
import os
import re
import datetime


#################################
####### CONNECTING TO DB ########
#################################

client_url = os.environ.get("DB_URL")
if not client_url:
    DB_URL = settings.DB_URL
client = pymongo.MongoClient(DB_URL)
db = client[settings.DB]


################################
######### EMULATION ############
################################

# transforms a db found doc for user reading
def to_gui(doc):
    _id = doc["_id"]
    doc = doc["body"]
    doc["_id"] = _id
    return doc


# transforms user submitted doc for db writing
def to_db(_doc, service):
    doc = {}
    if "_id" in _doc:
        doc["_id"] = _doc["_id"]
        del _doc['_id']
    doc["service"] = service
    doc["body"] = _doc
    return doc


# transforms a query/update field name for db
def to_db_field(field):
    if field == "_id":
        return field
    else:
        return f"body.{field}"


# transforms user query for db
# safe since ops are for values not fields
def q_t(_q, service):
    q = {"service": service}
    for field in _q:
        q[to_db_field(field)] = _q[field]
    return q


# transforms users update for db
# safe because ops are for values not fields
def u_t(_u):
    u = {}
    for op in _u:
        u[op] = {}
        for field in _u[op]:
            u[op][to_db_field(field)] = _u[op][field]
    return u

###############################
###### PHONE_NUMBER FUNCTIONS ########
###############################

def set_phone_number(phone_number,username):
    #TODO if your phone_number is not verified in a week, purge everything...
    phone_number_collection = db['web10']['phone_number']
    phone_number_collection.insert_one({"phone_number":phone_number,"username":username,"date":datetime.datetime.now()})
    db[username].udpate_one(q_t({"service":"services"}),u_t({"phone_number":phone_number}))

def get_phone_number(username):
    phone_number_collection = db['web10']['phone_number']
    res = phone_number_collection.find_one({"username":username})
    if res: 
        if "phone_number" in res : 
            return res["phone_number"]
    return None

def phone_number_taken(phone_number):
    phone_number_collection = db['web10']['phone_number']
    return phone_number_collection.find_one({"phone_number":phone_number})

################################
####### USER FUNCTIONS #########
################################

def get_term_record(username,service):
    query = q_t({"service": service},'services')
    record = db[f"{username}"].find_one(query)
    if record==None:
        return None
    return to_gui(record)

def get_star(user):
    return get_term_record(user,"*")

# sets an phone_number address to verified
def set_verified(user,verified=True):
    return db[user].update_one(
    q_t({"service": "*"},'services'),
    u_t({"$set":{"verified":verified}})
    )

# sets an phone_number address to verified
def is_verified(user):
    return get_star(user)["verified"]


def get_user(username: str):
    doc = get_star(username)
    if doc == None:
        raise exceptions.NO_USER
    return models.dotdict(doc)


def create_user(form_data, hash):
    username, password, phone_number = form_data.username, form_data.password, form_data.phone
    if username == "web10":
        raise exceptions.RESERVED
    if get_star(username):
        raise exceptions.EXISTS
    if settings.VERIFY:
        if phone_number_taken(phone_number):
            raise exceptions.PHONE_NUMBER_TAKEN
        #do this as early as possible TODO dangerous?
        set_phone_number(phone_number,username)
    # (*) record that holds both username and the password
    new_user = records.star_record()
    new_user["username"] = username
    new_user["hashed_password"] = hash(password)
    new_user = to_db(new_user,"services")

    # (services) record that allows auth.localhost to modify service terms
    services_terms = to_db(records.services_record(),"services")

    # insert the records to create / sign up the user
    user_col = db[username]
    user_col.insert_one(new_user)
    set_phone_number(phone_number,username)
    user_col.insert_one(services_terms)
    return "success"

def change_pass(user,new_pass,hash):
    q = q_t({"service":"*"},"services")
    u = u_t({"$set":{"hashed_password":hash(new_pass)}})
    db[user].update_one(q,u)
    return "success"

##########################
######### CRUD ###########
##########################


def create(user, service, _data):
    if star_found([_data]):
        raise exceptions.DSTAR
    data = to_db(_data,service)
    result = db[f"{user}"].insert_one(data)
    _data["_id"] = str(result.inserted_id)
    return _data


def read(user, service, query):
    query = q_t(query,service)
    records = db[f"{user}"].find(query)
    records = [to_gui(record) for record in records]
    for record in records:
        if record["_id"]:
            record["_id"] = str(record["_id"])
    return records


def update(user, service, query, update):
    if "_id" in query:
        query["_id"] = ObjectId(query["_id"])

    # Star Checking !
    if star_selected(user, service, query):
        raise exceptions.STAR
    for op in update:
        for item in update[op]:
            if item == "service" and update[op][item] == "*":
                raise exceptions.DSTAR
    query=q_t(query,service)
    update=u_t(update)
    db[f"{user}"].update_one(query, update)
    return "success"


def delete(user, service, query):
    if "_id" in query:
        query["_id"] = ObjectId(query["_id"])
    if star_selected(user, service, query):
        raise exceptions.STAR
    query=q_t(query,service)
    db[f"{user}"].delete_many(query)
    return "success"


##########################
#### Star Protection #####
##########################

# returns true if star service is inside the input
def star_found(services_docs):
    star = list(filter(lambda x: "service" in x and x["service"] == "*", services_docs))
    if len(star) > 0:
        return True
    return False


# sees if a mongodb query selects the star service
def star_selected(user, service, query):
    if service == "services":
        records = read(user, service, query)
        return star_found(records)
    return False

##########################
# customer id, + numbers
##########################

def get_customer_id(user):
    star = get_star(user)
    if "customer_id" in star:
        return star["customer_id"]
    return None
    
def set_customer_id(user,customer_id):
    return db[user].update_one(
        q_t({"service": "*"},'services'),
        u_t({"$set":{"customer_id":customer_id}})
    )

##########################
### General Protection ###
##########################


def is_in_cross_origins(site, username, service):
    record = get_term_record(username,service)
    if record == None:
        return False
    matches = list(filter(lambda x: re.fullmatch(site, x), record["cross_origins"]))
    return len(matches) > 0

def get_approved(username, provider, owner, service, action):
    record = get_term_record(owner,service)
    if record == None:
        return False
    if (username == owner) and (provider == settings.PROVIDER):
        return True

    def is_listed(e):
        list_hit = (bool(re.fullmatch(e["username"], username))) and (
            bool(re.fullmatch(e["provider"], provider))
        )
        action_permitted = action in e and e[action] == True
        all_permitted = "all" in e and e["all"] == True
        return list_hit and (action_permitted or all_permitted)

    if "whitelist" not in record:
        on_whitelist = False
    else:
        on_whitelist = len(list(filter(is_listed, record["whitelist"]))) > 0

    if "blacklist" not in record:
        on_blacklist = False
    else:
        on_blacklist = len(list(filter(is_listed, record["blacklist"]))) > 0
    return not (on_blacklist) and on_whitelist


###################
### Limits #######
#################


def decrement(user, action):
    query = q_t({"service": "*"},"services")
    cost = settings.COST[action]
    print(cost)
    update = u_t({"$inc": {"credits": - cost}})
    db[f"{user}"].update_one(query, update)

def should_replenish(user):
    # user would have to exist at this point ..
    star = get_star(user)
    return star["last_replenish"].month != datetime.datetime.now().month

def replenish(user):    
    query = q_t({"service": "*"},"services")    
    update = u_t({
            "$max": {
                "credits": settings.FREE_CREDITS,
            },
            "$currentDate": {"last_replenish": True},
        })
    db[f"{user}"].update_one(query,update)

def get_collection_size(user):
    return db.command("collstats", user)["size"]


# finds if a user is out of units
def has_credits(user):
    return get_star(user)["credits"] >= 0


# computes if a user is out of dbspace
def has_space(user):
    use = get_collection_size(user)
    star = get_star(user)
    amt = star["storage_capacity_mb"] * 1024 * 1024
    return amt > use
