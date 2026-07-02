from app import create_app
import os

app = create_app()
with app.app_context():
    print(f"MAIL_SUPPRESS_SEND: {app.config.get('MAIL_SUPPRESS_SEND')}")
    print(f"MAIL_SERVER: {app.config.get('MAIL_SERVER')}")
    print(f"MAIL_DEFAULT_SENDER: {app.config.get('MAIL_DEFAULT_SENDER')}")
    print(f"APP_ENV: {app.config.get('APP_ENV')}")
    print(f"SHOW_RESET_DEBUG_TOKEN: {app.config.get('SHOW_RESET_DEBUG_TOKEN')}")
