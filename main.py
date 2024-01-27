import requests
import sqlite3
import re
import json
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime
from pyppeteer import launch

from selenium import webdriver
from selenium.webdriver.common.keys import Keys


# Define a fixed database name
DB_NAME = "web_data.db"
api_key = "your_captcha_service_api_key"  # Replace with your actual API key


# Create database if it doesn't exist
def create_database():
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS web_pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT,
                title TEXT,
                headings TEXT,
                paragraphs TEXT,
                lists TEXT,
                code_snippets TEXT,
                publication_date TEXT
            )
        ''')
        conn.commit()
        conn.close()
        print(f"Database '{DB_NAME}' created successfully.")
    except sqlite3.Error as e:
        print("Error:", str(e))

# Store data in the fixed database with structured format
def store_data(url, title, headings, paragraphs, lists, code_snippets):
    try:
        publication_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('''
            INSERT INTO web_pages (
                url, title, headings, paragraphs, lists, code_snippets, publication_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (url, title, json.dumps(headings), json.dumps(paragraphs), json.dumps(lists), json.dumps(code_snippets), publication_date))
        conn.commit()
        conn.close()
        print("Data successfully saved to the database.")
    except sqlite3.Error as e:
        print("Error:", str(e))

# Web Scraping
async def scrape_web_page(url):
    browser = await launch(headless=True)
    page = await browser.newPage()
    await page.goto(url)
    page_content = await page.content()
    await browser.close()

    soup = BeautifulSoup(page_content, 'html.parser')

    title = soup.title.string if soup.title else 'No Title Found'
    headings = [tag.get_text().strip() for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])]
    paragraphs = [tag.get_text().strip() for tag in soup.find_all('p')]
    lists = [tag.get_text().strip() for tag in soup.find_all(['ul', 'ol'])]
    code_snippets = [tag.get_text().strip() for tag in soup.find_all('code')]

    # Debug prints
    print(f"Title: {title}")
    print(f"Headings: {len(headings)} found")
    print(f"Paragraphs: {len(paragraphs)} found")
    print(f"Lists: {len(lists)} found")
    print(f"Code Snippets: {len(code_snippets)} found")

    return title, headings, paragraphs, lists, code_snippets


# To call the async scrape function
def get_scraped_data(url):
    return asyncio.get_event_loop().run_until_complete(scrape_web_page(url))


def clean_text(text, is_code=False):
    """
    Clean the extracted text based on its type.
    :param text: The text to be cleaned.
    :param is_code: Flag to indicate if the text is a code snippet.
    :return: Cleaned text.
    """
    # Remove HTML tags
    clean = re.compile('<.*?>')
    cleaned_text = re.sub(clean, '', text)

    if not is_code:
        # For regular text, remove special characters and extra spaces
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)

    return cleaned_text.strip()

# Define a function to check robots.txt
def check_robots_txt(url):
    try:
        robots_url = url.rstrip('/') + '/robots.txt'
        response = requests.get(robots_url)
        if response.status_code == 200:
            # Parse the robots.txt content
            robots_txt_content = response.text
            return robots_txt_content
        else:
            return None
    except Exception as e:
        return None

# Check for CAPTCHA or JavaScript Challenges
def check_for_challenges(page_content):
    # Combining both CAPTCHA and JavaScript challenge keywords
    challenge_keywords = ['captcha', 'verification', 'challenge', 'javascript', 'verify', 'human']

    # Convert page_content to lower case only once for efficiency
    page_content_lower = page_content.lower()

    # Using regular expressions for a more accurate search
    # This helps in avoiding false positives that might occur with simple substring searches
    for keyword in challenge_keywords:
        if re.search(r'\b' + re.escape(keyword) + r'\b', page_content_lower):
            return True

    return False

async def solve_captcha_and_scrape(url, api_key):
    # Launch the browser
    browser = await launch(headless=False)
    page = await browser.newPage()
    await page.goto(url)

    try:
        # Check if there's a CAPTCHA on the page
        captcha_image = await page.querySelector('selector-for-captcha-image')
        if captcha_image:
            # Get the image source or data
            captcha_data = await page.evaluate('(captcha) => captcha.src', captcha_image)

            # Asynchronously send the CAPTCHA data to the solving service
            async with aiohttp.ClientSession() as session:
                async with session.post('https://api.captcha-service.com/solve', data={'key': api_key, 'data': captcha_data}) as response:
                    response_json = await response.json()
                    captcha_solution = response_json.get('solution')

            # Check if a solution was received
            if captcha_solution:
                # Enter the solution on the page
                input_field = await page.querySelector('selector-for-captcha-input')
                await input_field.type(captcha_solution)

                # Submit the CAPTCHA form or trigger necessary JavaScript
                submit_button = await page.querySelector('selector-for-submit-button')
                await submit_button.click()
            else:
                print("No captcha solution received.")
                return None

        # Continue with scraping...
        page_content = await page.content()
        soup = BeautifulSoup(page_content, 'html.parser')
        # Scrape the data as needed
        # ...

    except Exception as e:
        print(f"An error occurred: {e}")
        return None

    finally:
        await browser.close()

    return soup  # or return specific scraped data

async def check_for_initial_challenges(url):
    try:
        browser = await launch(headless=True)
        page = await browser.newPage()
        await page.goto(url, waitUntil='domcontentloaded')
        page_content = await page.content()
        await browser.close()

        # Here, you're using the same challenge checking logic
        return check_for_challenges(page_content)

    except Exception as e:
        print(f"Error during initial challenge check: {e}")
        return False


def choose_solver():
    while True:
        choice = input("Do you want to manually solve challenges (enter 'manual') or use the automated solver (enter 'auto')? ").lower()
        if choice in ['manual', 'auto']:
            return choice
        else:
            print("Invalid choice. Please enter 'manual' or 'auto'.")



if __name__ == "__main__":
    create_database()
    api_key = "your_captcha_service_api_key"  # Replace with your actual API key

    while True:
        web_page_url = input("Enter the URL of the website you want to collect data from (or type 'exit' to finish): ")

        if web_page_url.lower() == 'exit':
            break

        if not web_page_url.startswith(('http://', 'https://')):
            print("Invalid URL. Please enter a valid URL that starts with http:// or https://")
            continue

        robots_txt_content = check_robots_txt(web_page_url)
        if robots_txt_content is not None:
            print("Robots.txt content:")
            print(robots_txt_content)
            # Optionally, add logic to respect the rules in robots.txt here
        else:
            print("No robots.txt file found or unable to fetch it.")

        # Prompt the user for their choice
        challenge_choice = choose_solver()

        if challenge_choice == 'manual':
            print("You chose to manually solve challenges. Opening the page in a browser window...")

            # Initialize the Selenium WebDriver (Chrome in this example)
            driver = webdriver.Chrome()  # You'll need to download and configure the Chrome WebDriver
            driver.get(web_page_url)

            # Provide instructions to the user
            print("Please manually solve any challenges on the web page and fetch the data you need.")
            input("Press Enter to continue after solving challenges and extracting data...")

            # Close the browser window
            driver.quit()

        elif challenge_choice == 'auto':
            print("You chose to use the automated solver.")
            # Perform initial check for challenges
            has_challenges = asyncio.get_event_loop().run_until_complete(check_for_initial_challenges(web_page_url))

            if has_challenges:
                print("CAPTCHA or JavaScript challenges detected. Attempting to solve...")
                soup = asyncio.get_event_loop().run_until_complete(solve_captcha_and_scrape(web_page_url, api_key))
                if not soup:
                    print("Unable to solve CAPTCHA. Skipping this website.")
                    continue
            else:
                # If no challenges, proceed to scrape the web page
                title, headings, paragraphs, lists, code_snippets = asyncio.get_event_loop().run_until_complete(get_scraped_data(web_page_url))

                # Cleaning the extracted data
                cleaned_headings = [clean_text(heading) for heading in headings]
                cleaned_paragraphs = [clean_text(paragraph) for paragraph in paragraphs]
                cleaned_lists = [clean_text(list_item) for list_item in lists]
                cleaned_code_snippets = [clean_text(code, is_code=True) for code in code_snippets]

                # Storing the cleaned data
                if title and (cleaned_headings or cleaned_paragraphs or cleaned_lists or cleaned_code_snippets):
                    store_data(web_page_url, title, cleaned_headings, cleaned_paragraphs, cleaned_lists, cleaned_code_snippets)
                    print("Web page data processed and stored successfully.")
                else:
                    print("No valid data extracted from the web page.")

        print("Enter another URL or type 'exit' to finish.")

    print("Scraping session completed.")
