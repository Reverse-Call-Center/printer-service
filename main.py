from flask import Flask, request, jsonify
from flask_restx import Api, Resource, fields
import random
import string
import datetime
from escpos.printer import Usb
from PIL import Image
import qrcode
import requests

VENDOR_ID  = 0x04b8
PRODUCT_ID = 0x0202
INTERFACE  = 0

p = Usb(VENDOR_ID, PRODUCT_ID, interface=INTERFACE, timeout=0, in_ep=0x82, out_ep=0x01)

app = Flask(__name__)
api = Api(
    app, 
    version='1.0', 
    title='Printer Service API',
    description='A service for printing Bitcoin purchase receipts',
    doc='/swagger/'
)

receipt_response_model = api.model('ReceiptResponse', {
    'status': fields.String(description='Operation status'),
    'userId': fields.String(description='User ID'),
    'redemptionCode': fields.String(description='Generated redemption code')
})

error_response_model = api.model('ErrorResponse', {
    'error': fields.String(description='Error message')
})

@api.route('/CreateReceipt')
class CreateReceipt(Resource):
    @api.doc(
        description='Print a Bitcoin purchase receipt',
        params={'userId': 'User ID for the receipt'}
    )
    @api.response(200, 'Receipt printed successfully', receipt_response_model)
    @api.response(500, 'Print failed', error_response_model)
    def post(self):
        """Print a Bitcoin purchase receipt"""
        user_id = request.args.get('userId')
        
        if not user_id:
            print(f"Missing userId parameter")
            return {'error': 'Missing userId parameter'}, 400

        print(f"Received request for userId: {user_id}")
        
        # Call external API to get receipt data
        url = "http://192.168.1.51:5008/Receipt/create?userId={}".format(user_id)
        print(f"Calling external API: {url}")
        
        try:
            response = requests.post(url, timeout=10)  # Add timeout
            print(f"API response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"API error: {response.status_code} - {response.text}")
                return {'error': f'API error: {response.status_code}'}, 500
                
            data = response.json()
            print(f"API response data: {data}")
            
        except requests.exceptions.Timeout:
            print("API request timed out")
            return {'error': 'External API timeout'}, 500
        except requests.exceptions.ConnectionError:
            print("Failed to connect to external API")
            return {'error': 'Cannot connect to external API'}, 500
        except Exception as e:
            print(f"API request failed: {str(e)}")
            return {'error': f'API request failed: {str(e)}'}, 500

        # Generate receipt data
        random_chars = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        now = datetime.datetime.now()
        formatted_date = now.strftime('%m/%d/%y %H:%M')
        
        print(f"Generated redemption code: {random_chars}")
        
        try:
            # Print receipt
            print("Starting to print receipt...")
            p.set(align="center", bold=True, width=2, height=2)
            p.text("{}\n".format(data['brand']['name']))
            p.text("Bitcoin Purchase\n")
            p.set(align="left", bold=False, width=1, height=1)
            p.text("Date: {}\n".format(formatted_date))
            p.text("Transaction ID: {}\n\n".format(random_chars))
            p.text("REDEMPTION CODE: {}\n\n".format(random_chars))
            p.set(align="center", bold=False, width=1, height=1)
            p.text("To redeem your Bitcoin, visit:\n")
            p.text("https://{}/{}\n\n".format(data['brand']['domain'], random_chars))
            p.set(align="left", bold=False, width=1, height=1)
            p.text("Support: 1-810-206-2181")
            p.text("\n")
            p.text("\n")
            p.set(align="center", bold=False, width=2, height=2)
            p.text("Thank you!")
            p.cut()
            
            print("Receipt printed successfully")
            return {'status': 'Receipt printed', 'userId': user_id, 'redemptionCode': random_chars}, 200
        except Exception as e:
            print(f"Print failed: {str(e)}")
            return {'error': f'Print failed: {str(e)}'}, 500

if __name__ == "__main__":
    print("Printer service is running...")
    print("Swagger UI available at: http://localhost:5000/swagger/")
    app.run(host="0.0.0.0", port=5000)
