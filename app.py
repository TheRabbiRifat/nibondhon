from flask import Flask, request, jsonify, session
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import base64
from io import BytesIO
import time
import threading

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Replace with a secure secret key

# Configure Chrome options
chrome_options = Options()
chrome_options.add_argument("--headless")  # Run in headless mode
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# Global variable to store the session and WebDriver instances
driver = None
session_obj = None

# Function to clean up the session after 5 minutes
def cleanup_session():
    global driver, session_obj
    time.sleep(300)  # Wait for 5 minutes
    if driver:
        driver.quit()
        driver = None
    session_obj = None

@app.route('/api/v1/initiate', methods=['POST'])
def initiate_session():
    global driver, session_obj
    
    # Start a session
    session_obj = requests.Session()

    # Initialize a session with the third-party website
    url = 'https://everify.bdris.gov.bd'  # Replace with the actual URL
    try:
        response = session_obj.get(url, verify=False, timeout=20)  # SSL verification enabled
    except requests.exceptions.SSLError as e:
        return jsonify({'status': 'error', 'message': f'SSL Error: {str(e)}'}), 500
    
    # Process the response to extract the CAPTCHA and session ID
    if response.status_code == 200:
        # Use Selenium to handle CAPTCHA if necessary
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.get(url)
        
        # Extract the CAPTCHA image
        captcha_element = driver.find_element(By.ID, 'CaptchaImage')
        captcha_image = captcha_element.screenshot_as_png
        
        # Convert CAPTCHA image to Base64 and determine the format
        buffered = BytesIO(captcha_image)
        captcha_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

        # Determine image format (PNG in this example)
        captcha_format = 'png'
        data_url = f"data:image/{captcha_format};base64,{captcha_base64}"

        # Save the session details
        session['session_id'] = session_obj.cookies.get_dict()

        # Start a thread to clean up the session after 5 minutes
        cleanup_thread = threading.Thread(target=cleanup_session)
        cleanup_thread.start()

        return jsonify({
            'status': 'captcha_required',
            'captcha_image': data_url,
            'session_id': session['session_id']
        })
    else:
        return jsonify({'status': 'error', 'message': 'Failed to initiate session'}), response.status_code

@app.route('/api/v1/submit', methods=['POST'])
def submit_form():
    global driver, session_obj
    data = request.json
    
    # Retrieve session ID and create a session with it
    session_id = data.get('session_id')
    captcha_solution = data.get('captcha_solution')
    birth_date = data.get('birth_date')
    ubrn = data.get('ubrn')
    
    if not session_id or not captcha_solution or not birth_date or not ubrn:
        return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400

    # Start a session with the existing session ID
    session_obj.cookies.update(session_id)

    # Fill in the form fields
    driver.find_element(By.ID, 'CaptchaInputText').send_keys(captcha_solution)
    driver.find_element(By.ID, 'BirthDate').send_keys(birth_date)
    driver.find_element(By.ID, 'ubrn').send_keys(ubrn)
    
    # Submit the form
    driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()

    # Extract the result from the page
    result_element = driver.find_element(By.CSS_SELECTOR, ".body-content")
    result_html = result_element.get_attribute('outerHTML')

    # Close the Selenium driver
    driver.quit()
    driver = None
    session_obj = None

    return jsonify({'status': 'success', 'result': result_html})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
