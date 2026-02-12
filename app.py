from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber
import re
import io
import base64
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Allow requests from n8n

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'status': 'API is running',
        'version': '1.0',
        'endpoints': {
            '/extract-kern-pdf': 'POST - Extract data from KERN PDF'
        }
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

@app.route('/extract-kern-pdf', methods=['POST'])
def extract_kern_pdf():
    try:
        # Get PDF from request
        data = request.get_json()
        
        if not data or 'pdf_base64' not in data:
            return jsonify({
                'error': 'Missing pdf_base64 in request body'
            }), 400
        
        # Decode base64 PDF
        pdf_base64 = data['pdf_base64']
        pdf_binary = base64.b64decode(pdf_base64)
        
        # Extract text from PDF
        with pdfplumber.open(io.BytesIO(pdf_binary)) as pdf:
            text = pdf.pages[0].extract_text()
            
            # Extract Order Number (Ihr Zeichen)
            order_no_match = re.search(r'Ihr Zeichen\s+(\d+)', text)
            order_no = order_no_match.group(1) if order_no_match else None
            
            # Extract Shipment Date - looks for date before "Stk" (quantity)
            shipment_date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})\s+\d+\s*Stk', text)
            shipment_date_de = shipment_date_match.group(1) if shipment_date_match else None
            
            # Convert to DD/MM/YYYY format
            shipment_date = shipment_date_de.replace('.', '/') if shipment_date_de else None
            
            # Extract Subtotal (Zwischensumme EUR)
            subtotal_match = re.search(r'Zwischensumme\s+EUR\s+([\d.,]+)', text)
            subtotal_de = subtotal_match.group(1) if subtotal_match else None
            
            # Convert European format (1.234,56) to US format (1234.56)
            subtotal = None
            if subtotal_de:
                subtotal = float(subtotal_de.replace('.', '').replace(',', '.'))
            
            # Check if shipment is today
            is_today = False
            if shipment_date:
                try:
                    ship_date = datetime.strptime(shipment_date, '%d/%m/%Y').date()
                    is_today = ship_date == datetime.now().date()
                except:
                    pass
            
            # Extract Document Number for reference
            doc_no_match = re.search(r'Belegnummer\s+([\d\-]+)', text)
            doc_no = doc_no_match.group(1) if doc_no_match else None
            
            # Return extracted data
            return jsonify({
                'success': True,
                'data': {
                    'order_no': order_no,
                    'shipment_date': shipment_date,
                    'subtotal': subtotal,
                    'is_shipment_today': is_today,
                    'document_no': doc_no
                },
                'raw_text_preview': text[:500]  # First 500 chars for debugging
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # For local testing
    app.run(host='0.0.0.0', port=8080, debug=True)
