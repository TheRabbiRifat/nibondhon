import base64
import requests
import pdfkit
import fitz  # PyMuPDF
from flask import Flask, request, jsonify, session
from flask_session import Session
from bs4 import BeautifulSoup
import io

app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['PERMANENT_SESSION_LIFETIME'] = 300  # 5 minutes
Session(app)

@app.route('/initiate', methods=['POST'])
def initiate_session():
    url = 'https://everify.bdris.gov.bd'
    
    try:
        session.clear()
        session['requests_session'] = requests.Session()
        session['requests_session'].headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36'
        })
        
        response = session['requests_session'].get(url, verify=False, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')

        # Generate PDF from the page content
        pdf = pdfkit.from_string(response.text, False)

        # Extract images from the generated PDF
        images = extract_images_from_pdf(pdf)

        # Extract hidden inputs
        hidden_inputs = {}
        for hidden_input in soup.find_all("input", type="hidden"):
            hidden_inputs[hidden_input.get("name")] = hidden_input.get("value", "")

        return jsonify({
            'status': 'captcha_required',
            'images': images,
            'session_id': session.sid,
            'hidden_inputs': hidden_inputs  # Include hidden inputs in the response
        })
    
    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'Request Error', 'details': str(e)}), 500


def extract_images_from_pdf(pdf_data):
    images = []
    
    # Use PyMuPDF (fitz) to extract images from the PDF
    pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
    
    for page_index in range(len(pdf_document)):
        page = pdf_document[page_index]
        for image_index, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            base_image = pdf_document.extract_image(xref)
            image_bytes = base_image["image"]
            image_extension = base_image["ext"]
            image_base64 = f"data:image/{image_extension};base64," + base64.b64encode(image_bytes).decode('utf-8')
            images.append(image_base64)
    
    pdf_document.close()
    return images

@app.route('/submit', methods=['POST'])
def submit_form():
    data = request.json
    session_id = data.get('session_id')
    
    if not session_id or 'requests_session' not in session:
        return jsonify({'error': 'Invalid session'}), 400
    
    form_data = {
        'CaptchaInputText': data.get('captcha'),
        'BirthDate': data.get('birth_date'),
        'UBRN': data.get('serial_number')
    }
    
    # Add hidden fields back to form_data
    hidden_inputs = data.get('hidden_inputs', {})
    form_data.update(hidden_inputs)

    try:
        # Use the existing session and page to submit the form
        previous_page_url = 'https://everify.bdris.gov.bd'
        soup = BeautifulSoup(session['requests_session'].get(previous_page_url, verify=False, timeout=10).text, 'html.parser')
        form = soup.find('form')
        submit_url = previous_page_url + form['action']

        form_data['btn'] = 'Search'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': previous_page_url,
        }
        
        response = session['requests_session'].post(submit_url, data=form_data, headers=headers, verify=False, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        main_div = soup.find('div', {'id': 'mainContent'})  # Replace 'mainContent' with actual div ID
        
        return jsonify({
            'status': 'success',
            'content': str(main_div)
        })
    
    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'Request Error', 'details': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
