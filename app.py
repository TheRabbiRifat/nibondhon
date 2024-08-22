import base64
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Set up session with TLS 1.2 support
session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36'})

@app.route('/initiate', methods=['POST'])
def initiate_session():
    url = 'https://everify.bdris.gov.bd'
    
    try:
        response = session.get(url, verify=False, timeout=50)
        response.raise_for_status()
        
        captcha_img_src = extract_captcha_image_src(response.text)
        captcha_image_url = url + captcha_img_src
        captcha_image = session.get(captcha_image_url, verify=True, timeout=10)
        captcha_image.raise_for_status()
        
        captcha_image_base64 = base64.b64encode(captcha_image.content).decode('utf-8')
        
        return jsonify({
            'status': 'captcha_required',
            'captcha_image': captcha_image_base64
        })
    
    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'Request Error', 'details': str(e)}), 500

@app.route('/submit', methods=['POST'])
def submit_form():
    data = request.json
    
    form_data = {
        'CaptchaInputText': data.get('captcha'),
        'BirthDate': data.get('birth_date'),
        'UBRN': data.get('serial_number')
    }
    
    try:
        submit_url = 'https://everify.bdris.gov.bd/some_endpoint'
        response = session.post(submit_url, data=form_data, verify=True, timeout=10)
        response.raise_for_status()
        
        body_content = extract_body_content(response.text)
        
        return jsonify({
            'status': 'success',
            'content': body_content
        })
    
    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'Request Error', 'details': str(e)}), 500

def extract_captcha_image_src(html):
    # Implement your logic to extract captcha image URL
    return '/DefaultCaptcha/Generate?t=7009b429c55f4d6f9ee59119387c42f3'

def extract_body_content(html):
    # Implement your logic to extract the required div
    return "Extracted body content here."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
