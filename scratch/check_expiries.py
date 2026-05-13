import os
from dotenv import load_dotenv
from truedata_rest_api import TrueDataRestAPI

load_dotenv()
api = TrueDataRestAPI(username=os.getenv("TRUEDATA_USERNAME"), password=os.getenv("TRUEDATA_PASSWORD"))
print("NIFTY Expiries:", api.get_expiry_list("NIFTY"))
print("CRUDEOIL Expiries:", api.get_expiry_list("CRUDEOIL"))
