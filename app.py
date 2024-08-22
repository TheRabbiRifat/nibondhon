from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from apscheduler.schedulers.background import BackgroundScheduler
import base64
import time
import uuid
import requests
import datetime
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key')  # Use environment variable or fallback

# In-memory storage for browser sessions
browser_sessions = {}

# Scheduler for cleaning up expired sessions
scheduler = BackgroundScheduler()
scheduler.start()

# Configure Chrome options
chrome_options = Options()
chrome_options.add_argument("--headless")  # Run in headless mode
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# Session timeout in seconds (5 minutes)
SESSION_TIMEOUT = 300

def cleanup_expired_sessions():
    current_time = datetime.datetime.now()
    expired_sessions = [session_id for session_id, session_data in browser_sessions.items()
                        if (current_time - session_data['start_time']).total_seconds() > SESSION_TIMEOUT]
    
    for session_id in expired_sessions:
        session_data = browser_sessions.pop(session_id, None)
        if session_data:
            session_data['driver'].quit()
            print(f"Closed expired session: {session_id}")

# Schedule session cleanup every minute
scheduler.add_job(cleanup_expired_sessions, 'interval', minutes=1)

@app.route('/api/v1/initiate', methods=['POST'])
def initiate_session():
    data = request.json
    
    # Extract and validate inputs
    date_of_birth = data.get('date_of_birth')
    serial_number = data.get('serial_number')

    if not date_of_birth or not serial_number:
        return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400

    # Generate a unique session ID
    session_id = str(uuid.uuid4())

    # Start a new Selenium WebDriver session
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    # Navigate to the target page
    url = 'https://everify.bdris.gov.bd'  # Replace with the actual URL
    driver.get(url)

    try:
        # Fill in the BirthDate field like a human
        birth_date_input = driver.find_element(By.ID, 'BirthDate')
        birth_date_input.click()
        for char in date_of_birth:
            birth_date_input.send_keys(char)
            time.sleep(0.2)  # Wait 200ms between keystrokes

        # Fill in the Serial Number (UBRN) field like a human
        ubrn_input = driver.find_element(By.ID, 'ubrn')
        ubrn_input.click()
        for char in serial_number:
            ubrn_input.send_keys(char)
            time.sleep(0.2)  # Wait 200ms between keystrokes

        # Locate the CAPTCHA image element by its ID
        captcha_element = driver.find_element(By.ID, 'CaptchaImage')

        # Extract the 'src' attribute to get the CAPTCHA image URL
        captcha_url = captcha_element.get_attribute('src')

        # Fetch the CAPTCHA image directly from the server
        captcha_response = requests.get(captcha_url)
        captcha_image = captcha_response.content

        # Convert CAPTCHA image to Base64
        captcha_base64 = base64.b64encode(captcha_image).decode('utf-8')

        # Store the driver session in memory associated with the session ID
        browser_sessions[session_id] = {
            'driver': driver,
            'start_time': datetime.datetime.now()
        }

        return jsonify({
            'status': 'captcha_required',
            'captcha_image': captcha_base64,
            'session_id': session_id
        })
    
    except Exception as e:
        driver.quit()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/v1/submit', methods=['POST'])
def submit_form():
    data = request.json
    
    # Retrieve the session ID and corresponding WebDriver instance
    session_id = data.get('session_id')
    captcha_solution = data.get('captcha_solution')

    if not session_id or session_id not in browser_sessions:
        return jsonify({'status': 'error', 'message': 'Invalid session ID'}), 400

    if not captcha_solution:
        return jsonify({'status': 'error', 'message': 'Missing CAPTCHA solution'}), 400

    # Retrieve the existing WebDriver session
    driver = browser_sessions[session_id]['driver']

    try:
        # Fill in the CAPTCHA input field like a human
        captcha_input = driver.find_element(By.ID, 'CaptchaInputText')
        captcha_input.click()
        for char in captcha_solution:
            captcha_input.send_keys(char)
            time.sleep(0.2)  # Wait 200ms between keystrokes

        # Click the submit button
        submit_button = driver.find_element(By.CSS_SELECTOR, 'input.btn.btn-primary[type="submit"]')
        submit_button.click()

        # Wait for the response and extract the specific div content
        time.sleep(2)  # Give time for the response to load
        body_content_div = driver.find_element(By.CLASS_NAME, 'body-content')
        response_data = body_content_div.get_attribute('outerHTML')

        return jsonify({'status': 'success', 'data': response_data})
    
    finally:
        # Close the browser session and remove it from memory
        driver.quit()
        del browser_sessions[session_id]

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
