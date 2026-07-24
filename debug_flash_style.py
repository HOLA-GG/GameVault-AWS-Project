from playwright.sync_api import sync_playwright
import os
import subprocess
import time

def run_test():
    # Start the Flask app
    env = os.environ.copy()
    env["FLASK_APP"] = "app"
    # Ensure we use a test database or similar if needed, but here we just need the UI

    process = subprocess.Popen(["flask", "run", "--port", "5001"], env=env)
    time.sleep(3) # Wait for app to start

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()

            # Go to login and trigger a flash error
            page.goto("http://127.0.0.1:5001/login")
            page.fill("#email", "wrong@example.com")
            page.fill("#password", "wrongpassword")
            page.click("button[type='submit']")

            # Wait for flash message
            page.wait_for_selector(".flash.error")

            flash_element = page.query_selector(".flash.error")
            color = page.evaluate("(el) => getComputedStyle(el).color", flash_element)
            background = page.evaluate("(el) => getComputedStyle(el).background", flash_element)

            print(f"FLASH ERROR COLOR: {color}")
            print(f"FLASH ERROR BACKGROUND: {background}")

            # Take a screenshot to confirm
            page.screenshot(path="verification/flash_debug.png")

            browser.close()
    finally:
        process.terminate()

if __name__ == "__main__":
    if not os.path.exists("verification"):
        os.makedirs("verification")
    run_test()
