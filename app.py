import base64
import requests
from flask import Flask, request, jsonify
import threading
import time
import uuid
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image
from io import BytesIO
from bs4 import BeautifulSoup

app = Flask(__name__)

# Dictionary to store sessions with their expiration time
sessions = {}

# Configure Chrome options
chrome_options = Options()
chrome_options.add_argument("--headless")  # Run in headless mode
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

def create_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36'
    })
    return session

@app.route('/initiate', methods=['POST'])
def initiate_session():
    session_id = str(uuid.uuid4())  # Generate a unique session ID
    url = 'https://everify.bdris.gov.bd'
    
    # Start a Selenium WebDriver session
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.get(url)
    
    try:
        # Trigger CAPTCHA by visiting the page
        time.sleep(3)  # Adjust as needed for CAPTCHA to load

        # Extract CAPTCHA image data
        captcha_img_element = driver.find_element(By.ID, 'CaptchaImage')
        captcha_img_url = captcha_img_element.get_attribute('src')

        # Get the image data and MIME type
        captcha_img_data_url = get_image_data_url(captcha_img_url)

        # Store the session and its expiration time
        sessions[session_id] = {
            'driver': driver,
            'captcha_img_data_url': captcha_img_data_url,
            'expires_at': time.time() + 300  # 5 minutes from now
        }
        
        return jsonify({
            'status': 'captcha_required',
            'captcha_image': captcha_img_data_url,
            'session_id': session_id
        })
    
    except Exception as e:
        return jsonify({'error': 'Request Error', 'details': str(e)}), 500
    finally:
        # Ensure the driver is properly closed if an error occurs
        if driver:
            driver.quit()

@app.route('/submit', methods=['POST'])
def submit_form():
    data = request.json
    session_id = data.get('session_id')
    captcha = data.get('captcha')
    ubrn = data.get('ubrn')
    birth_date = data.get('birth_date')

    if not session_id or not captcha or not ubrn or not birth_date:
        return jsonify({'error': 'Session ID, CAPTCHA, UBRN, and BirthDate are required'}), 400

    # Retrieve the session
    session_data = sessions.get(session_id)
    if not session_data or session_data['expires_at'] < time.time():
        return jsonify({'error': 'Session expired or invalid'}), 400
    
    # Use the stored Selenium driver
    driver = session_data['driver']

    try:
        # Fill in the form fields
        fill_form_field(driver, By.ID, 'CaptchaInputText', captcha)
        fill_form_field(driver, By.ID, 'ubrn', ubrn)
        fill_form_field(driver, By.ID, 'BirthDate', birth_date)

        # Click submit button to submit the form
        submit_button = driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
        ActionChains(driver).move_to_element(submit_button).click().perform()

        # Wait for the result to be loaded
        time.sleep(5)  # Adjust as needed for page load

        # Extract the main content of the response page
        main_content = extract_main_div(driver.page_source)
        
        return jsonify({
            'status': 'success',
            'content': main_content
        })
    
    except Exception as e:
        return jsonify({'error': 'Error during form submission', 'details': str(e)}), 500
    
    finally:
        # Optionally, close the driver when the session expires or is no longer needed
        if time.time() >= session_data['expires_at']:
            driver.quit()
            del sessions[session_id]

def fill_form_field(driver, by, element_id, value):
    """Simulate human typing in a form field"""
    field = driver.find_element(by, element_id)
    field.click()
    for char in value:
        field.send_keys(char)
        # Simulate human typing delay
        time.sleep(random.uniform(0.1, 0.3))

def extract_main_div(html):
    # Use BeautifulSoup to extract the main div
    soup = BeautifulSoup(html, 'html.parser')
    main_div = soup.find('div', {'id': 'main-content'})  # Adjust the selector as needed
    return main_div.prettify() if main_div else "Main content not found."

def get_image_data_url(img_url):
    """Get image data URL from image source URL"""
    response = requests.get(img_url, verify=False)  # Disable SSL verification
    img_data = response.content
    mime_type = response.headers['Content-Type']
    img_data_base64 = base64.b64encode(img_data).decode('utf-8')
    return f"data:{mime_type};base64,{img_data_base64}"

# Periodic cleanup function
def cleanup_sessions():
    while True:
        current_time = time.time()
        expired_sessions = [sid for sid, data in sessions.items() if data['expires_at'] < current_time]
        for sid in expired_sessions:
            sessions[sid]['driver'].quit()
            del sessions[sid]
        time.sleep(60)  # Check every minute

# Start the cleanup thread
cleanup_thread = threading.Thread(target=cleanup_sessions, daemon=True)
cleanup_thread.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
