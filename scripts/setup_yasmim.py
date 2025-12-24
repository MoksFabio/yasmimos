import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "yasmimos.settings")
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

# Try creating/getting Yasmim again explicitly
username = "Yasmim Poliana"
email = "polianayasmim27@gmail.com"
password = "yasmimos"
phone = "81984086846"

if not User.objects.filter(username=username).exists():
    print(f"Creating superuser {username}...")
    try:
        user = User.objects.create_superuser(username=username, email=email, password=password)
        user.phone_number = phone
        user.save()
        print("Superuser created successfully!")
    except Exception as e:
        print(f"Error creating user: {e}")
else:
    u = User.objects.get(username=username)
    print(f"User {u.username} verified. Is superuser: {u.is_superuser}")
    if not u.is_superuser:
        u.is_superuser = True
        u.is_staff = True
        u.save()
        print("Promoted to superuser.")
