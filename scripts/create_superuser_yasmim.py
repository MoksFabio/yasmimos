from django.contrib.auth import get_user_model
import os

User = get_user_model()

username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "Yasmim Poliana")
email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "polianayasmim27@gmail.com")
phone = os.environ.get("DJANGO_SUPERUSER_PHONE", "81984086846")
password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")

if not User.objects.filter(username=username).exists():
    print(f"Creating superuser {username}...")
    if not password:
        import secrets
        # Generate a strong random password if not provided
        password = secrets.token_urlsafe(16)
        print(f"WARNING: No password provided in environment (DJANGO_SUPERUSER_PASSWORD).")
        print(f"Generated a secure temporary password: {password}")
        print("Please change this password immediately after logging in.")

    try:
        user = User.objects.create_superuser(username=username, email=email, password=password)
        user.phone_number = phone
        user.save()
        print("Superuser created successfully!")
    except Exception as e:
        print(f"Error creating user: {e}")
else:
    print(f"User {username} already exists.")
