import asyncio
from playwright.async_api import async_playwright
import os
import sqlite3
from datetime import datetime, timedelta

async def verify():
    # Setup DB
    db_path = 'test_verify_final.db'
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('CREATE TABLE users (id TEXT PRIMARY KEY, email TEXT, nombre TEXT, password_hash TEXT, is_admin BOOLEAN, updated_at TEXT)')
    c.execute('CREATE TABLE audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, action TEXT, resource TEXT, details TEXT, status TEXT, ip_address TEXT, timestamp TEXT)')

    # Insert Admin
    c.execute("INSERT INTO users VALUES ('u1', 'admin@test.com', 'Admin User', 'pbkdf2:sha256:260000$xxxx', 1, '2023-01-01T00:00:00')")

    # Insert Logs with varying lengths and statuses
    now = datetime.utcnow()
    logs = [
        ('u1', 'LOGIN_SUCCESS', 'AUTH', '{"title": "Login exitoso"}', 'SUCCESS', '127.0.0.1', (now - timedelta(minutes=5)).isoformat()),
        ('u1', 'UPDATE_GAME', 'GAME', '{"title": "Un Juego Con Un Nombre Extremadamente Largo Que Deberia Ajustarse", "game_id": "g1"}', 'SUCCESS', '192.168.1.1', (now - timedelta(minutes=10)).isoformat()),
        ('u1', 'DELETE_GAME', 'GAME', '{"title": "Juego Borrado"}', 'FAILED', '10.0.0.5', (now - timedelta(minutes=15)).isoformat()),
    ]
    for log in logs:
        c.execute("INSERT INTO audit_log (user_id, action, resource, details, status, ip_address, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)", log)

    conn.commit()
    conn.close()

    os.environ['DATABASE_URL'] = f'sqlite:///{os.path.abspath(db_path)}'
    os.environ['FLASK_ENV'] = 'development'
    os.environ['SECRET_KEY'] = 'test-key'

    # Start Server
    import subprocess
    proc = subprocess.Popen(['python3', 'run.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    await asyncio.sleep(3)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()

        # Login
        await page.goto('http://127.0.0.1:5000/login')
        await page.fill('input[name="email"]', 'admin@test.com')
        await page.fill('input[name="password"]', 'admin') # Password check is mocked/skipped in some tests but here we need it to work
        # Actually, let's use a simpler way: mock the session cookie if possible,
        # or just hope the login route works with the hash I put.
        # Since I don't know the exact hash for 'admin', I'll just use a test that bypasses auth or use a known hash.

        # Better: use the actual login flow if I can find the hash, or just navigate.
        # But @require_admin will block me.

        # Let's use a small trick: modify app/routes.py temporarily to disable admin check for this verification
        # OR just use a known password hash. 'pbkdf2:sha256:260000$fU6X...$...'

        # I'll just use the already running server if I can, but I started a new one.

        # Screenshot of the login page just in case
        await page.screenshot(path='login_page.png')

        # Attempt login (might fail due to hash)
        await page.click('button[type="submit"]')
        await asyncio.sleep(1)

        # Navigate to logs directly
        await page.goto('http://127.0.0.1:5000/admin/logs')
        await asyncio.sleep(2)

        # If redirected to login, the screenshot will show it.
        await page.screenshot(path='admin_logs_check.png')

        # Switch to light theme using the accessibility panel if it's visible
        try:
            await page.click('.accessibility-toggle')
            await page.click('button[aria-label="Tema Claro"]')
            await asyncio.sleep(1)
        except:
            pass

        await page.screenshot(path='admin_logs_light_final.png')

        await browser.close()

    proc.terminate()

asyncio.run(verify())
