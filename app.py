import base64
import requests
from flask import Flask, request, jsonify, session
from flask_session import Session
from bs4 import BeautifulSoup
from weasyprint import HTML
import fitz  # PyMuPDF

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
        html_content = response.text
        pdf_file = HTML(string=html_content).write_pdf()

        # Save PDF to a file
        with open('page.pdf', 'wb') as f:
            f.write(pdf_file)

        # Open PDF and extract images
        doc = fitz.open('page.pdf')
        images = []
        for page in doc:
            for img in page.get_images(full=True):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                content_type = base_image["ext"]  # Usually png or jpeg
                images.append(f"data:image/{content_type};base64,{image_base64}")

        # Extract hidden inputs
        hidden_inputs = {}
        for hidden_input in soup.find_all("input", type="hidden"):
            hidden_inputs[hidden_input.get("name")] = hidden_input.get("value", "")

        return jsonify({
            'status': 'captcha_required',
            'captcha_images': images,
            'session_id': session.sid,
            'hidden_inputs': hidden_inputs
        })

    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'Request Error', 'details': str(e)}), 500

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
