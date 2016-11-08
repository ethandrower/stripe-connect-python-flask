
import time
import stripe
import urllib3
import certifi
import sys
import requests

stripe.api_key = "your key here"
from flask import Flask, request
from stripe import Customer
from flask import jsonify
app = Flask(__name__)



### api for stripe connect integration


# New customer, return their ID
@app.route("/stripe-add-customer", methods=["GET"])
def create_customer_stripe():
  try:
  
    #return "hello"
    customer = request.args.get("customer-description")
  
    var = stripe.Customer.create(
      description= customer
      ##source=  source will be a credit card token soon!
      )
    #print(var['id'], file=sys.stderr)
    #return jsonify(result=var['id'])
    return jsonify({"result": "success", "id": str(var['id']) })

  except Exception as e:
    return jsonify({"result": "failed", "reason": str(e.args[0]) })



# Add customer CC to their account.
@app.route("/stripe-update-customer", methods=["POST"])
def update_customer_stripe():
  try:
    payment_token = request.form["payment-token"]
    #customerID = request.form["customer-id"]
    customerID = request.form["customer-id"]
    cu = stripe.Customer.retrieve(customerID)
    cu.source = payment_token
    res = cu.save()
    print("result of save op is " + str(res))
    return jsonify({"result" : "success"})

  except Exception as e:
    
    return jsonify({"result": "failed", "reason": str(e.args[0])})


  
#untested so far. make a charge and specify the customer -> merchant.
@app.route("/stripe-charge", methods=["POST"])
def charge_customer():
  print("inside charge customer")

  try:
    source = request.form["customerID"]
    destinationID = request.form["merchantID"]
    print("merchant id is " + destinationID )
    price = int(float(request.form["price"]) * 100)
    response=stripe.Charge.create(
    amount= price,
    currency='usd',
    customer= source,
    destination = destinationID,
    application_fee = 500)
    return jsonify({"result": "success"})

  except Exception as e:
    print( "error making charge " + str(e.args[0])) 
    return jsonify({"result": "failed", "reason": str(e.args[0])} ) 


@app.route("/stripe-add-merchant", methods=["GET"])
def create_merchant():
  try:
    
    merch = stripe.Account.create( country='US', managed=True)
    print(merch)
    return jsonify({"result": "success", "merchant": merch})

  except Exception as e:
    return jsonify({"result": "failed", "reason": str(e.args[0])})
 


  # returns fields id,  and keys: { secret and perishable} #store keeys for authentication (if you need them)

@app.route("/tos-send-email", methods=["POST"])
def send_email():
  with open ( '/opt/emails/tos3.html', 'r') as f:
    email_text = f.read()
    email_text_utf8 = email_text.decode('utf-8').strip()
    stripeID = request.form['user_stripe_id']
    email_text_utf8 = email_text_utf8.replace("replaceme", "https:/your-api-domain.com/tos-accept?stripe_id="+ stripeID ) 
    url = "https://api.mailgun.net/v3/yourdomain.com/messages"

    res = requests.post(url, auth=("api", "key-here5"),
    data={"from": "admin@yourdomain.com",
    "to": request.form['user_email'],
    "subject": "Accept TOS",
    "html": email_text_utf8 })
    print("sent mail with status " + str(res))
    #"text": "Accept the terms of service for your id " + request.form['user_stripe_id']})
    return jsonify({"result": str(res) })

@app.route("/tos-accept", methods=["GET"])
def accept_tos():
  stripe_id = request.args.get("stripe_id")
  if (stripe_id.find("acct") != -1):
    #merchant
    merch = stripe.Account.retrieve(stripe_id)
    merch.tos_acceptance.date = int(time.time())
    merch.tos_acceptance.ip = request.remote_addr
    merch.save()
    return "Thank you for accepting the terms of service!"
  else:
    return "Thank you for accepting the terms of service!"

     

### stripe update merc
@app.route("/stripe-update-merchant", methods=["POST"])
def update_merch():

  fullName = request.form["first-name"] + ' ' + request.form["last-name"]
  birthday = request.form["birthday"]
  lastName = request.form["last-name"]
  firstName = request.form["first-name"]
  month = birthday[0:2]
  day = birthday[2:4]
  year = birthday[4:]

  routing = request.form["routing"]
  accountNumber = request.form["account"]
  merchID = request.form["merchant-id"]
  
  # not being used yet...
  address = request.form["address"]
  city = request.form["city"]
  zipCode = request.form["zip"]
  ssn = request.form["ssn"]

  try:

    account= stripe.Account.retrieve(merchID)
    if ( account is not None):
    #create new bank account if doesn't exist.
      bankToken = createNewBankAccountToken(fullName, routing, accountNumber)
      response = account.external_accounts.create(external_account=bankToken)
      account.legal_entity.last_name = lastName
      account.legal_entity.first_name = firstName
      account.legal_entity.type = "individual"  
      account.transfer_schedule.delay_days = 7
      account.transfer_schedule.interval = "daily"
      account.legal_entity.ssn_last_4 = ssn


      account.legal_entity.address.line1 = address
      account.legal_entity.address.city = city
      account.legal_entity.address.postal_code = zipCode
      account.legal_entity.address.state = "IL"


      if ( len(birthday) == 8):
        account.legal_entity.dob.day = day
        account.legal_entity.dob.month = month
        account.legal_entity.dob.year = year      
      else:
        raise ValueError('Birthday is not correct length. Please use MMDDYYYY format')
      account.save()

      return jsonify({"result" : "success" })
  except Exception as e:
    print("args " + str(e.args))
    #print("just e " + e)
  
    return jsonify({"result": "failed", "reason": str(e.args[0]) })



def createNewBankAccountToken(fullName, routing, accountNumber):
  print("account number is " + accountNumber)
  tok = stripe.Token.create(
    bank_account={
      "country": 'US',
      "currency": 'usd',
      "account_holder_name": fullName,
      "account_holder_type": 'individual',
      "routing_number": routing,
      "account_number": accountNumber
     },
   )
  return tok

#  merch = stripe.Account.update... 


###this is a route you can have a free alerting service like cabot hit to check if your parse server is alive

@app.route("/parselive", methods=["GET"])
def checkparse():
  headers = {"X-Parse-Application-Id": "appid", "X-Parse-Master-Key": "masterkey"}
  url = "http://yourparse-server.com:1337/parse/classes/SomeClass"
  try:

    r = requests.get(url, headers=headers)
  except Exception as e:
    return "dead"


  print("status of parselive is " + str(r.status_code))

  if r.status_code == 200:
    return "alive"
  else:
    return "dead"




if __name__ == "__main__":
  app.debug = True
  app.run()

