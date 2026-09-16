from playwright.sync_api import sync_playwright
import os
import subprocess
import time

def run_test():
    env = os.environ.copy()
    env["FLASK_APP"] = "app"

    process = subprocess.Popen(["flask", "run", "--port", "5002"], env=env)
    time.sleep(3)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto("http://127.0.0.1:5002/login")
            page.fill("#email", "wrong@example.com")
            page.fill("#password", "wrongpassword")
            page.click("button[type='submit']")

            page.wait_for_selector(".flash.error")

            flash_element = page.query_selector(".flash.error")

            data = page.evaluate("""(el) => {
                const style = getComputedStyle(el);
                return {
                    color: style.color,
                    backgroundColor: style.backgroundColor,
                    backgroundImage: style.backgroundImage,
                    opacity: style.opacity,
                    display: style.display,
                    visibility: style.visibility,
                    innerText: el.innerText,
                    innerHTML: el.innerHTML
                };
            }""", flash_element)

            print(f"DEBUG DATA: {data}")

            # Check if there are any other elements inside that might have their own color
            children_data = page.evaluate("""(el) => {
                return Array.from(el.querySelectorAll('*')).map(c => {
                    const s = getComputedStyle(c);
                    return {
                        tagName: c.tagName,
                        className: c.className,
                        color: s.color,
                        innerText: c.innerText
                    };
                });
            }""", flash_element)

            print(f"CHILDREN DATA: {children_data}")

            page.screenshot(path="verification/flash_debug_v2.png")
            browser.close()
    finally:
        process.terminate()

if __name__ == "__main__":
    if not os.path.exists("verification"):
        os.makedirs("verification")
    run_test()
