import os
import uuid
from werkzeug.security import generate_password_hash
from app import create_app
from app.models import User, AuditLog, get_session_factory, crear_log_audit

os.environ['DATABASE_URL'] = 'sqlite:///test_verification.db'
app = create_app()
with app.app_context():
    Session = get_session_factory()
    with Session() as session:
        # Create admin user
        admin = session.query(User).filter_by(email='admin@test.com').first()
        if not admin:
            admin = User(
                user_id=str(uuid.uuid4()),
                nombre='Admin',
                apellido='Test',
                email='admin@test.com',
                prefijo_pais='+57',
                telefono='1234567890',
                password_hash=generate_password_hash('admin123'),
                role='admin'
            )
            session.add(admin)
            session.commit()
            print(f"Admin created: {admin.user_id}")
        else:
            admin.password_hash = generate_password_hash('admin123')
            admin.role = 'admin'
            session.commit()
            print("Admin updated")

        user_id = admin.user_id

        # Use the helper function which correctly sets audit_id
        for i in range(5):
            crear_log_audit(
                user_id=user_id,
                action='LOGIN',
                resource='Auth',
                status='SUCCESS',
                ip_address='127.0.0.1',
                details={'title': f'Inicio de sesión exitoso {i}'}
            )
        print("Audit logs created.")
