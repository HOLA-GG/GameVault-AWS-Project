from playwright.sync_api import sync_playwright
import os
import subprocess
import time

def run_test():
    env = os.environ.copy()
    env["FLASK_APP"] = "app"

    process = subprocess.Popen(["flask", "run", "--port", "5003"], env=env)
    time.sleep(3)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto("http://127.0.0.1:5003/login")
            page.fill("#email", "wrong@example.com")
            page.fill("#password", "wrongpassword")
            page.click("button[type='submit']")

            page.wait_for_selector(".flash.error")
            flash_element = page.query_selector(".flash.error")

            # Monitor opacity over 1 second
            for i in range(10):
                opacity = page.evaluate("(el) => getComputedStyle(el).opacity", flash_element)
                print(f"OPACITY AT {i*100}ms: {opacity}")
                time.sleep(0.1)

            page.screenshot(path="verification/flash_debug_v3.png")
            browser.close()
    finally:
        process.terminate()

if __name__ == "__main__":
    if not os.path.exists("verification"):
        os.makedirs("verification")
    run_test()
