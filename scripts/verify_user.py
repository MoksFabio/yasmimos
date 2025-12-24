from django.contrib.auth import get_user_model
User = get_user_model()
u = User.objects.filter(username="Yasmim Poliana").first()
if u:
    print(f"VERIFIED: User {u.username} exists, is_superuser={u.is_superuser}")
else:
    print("VERIFIED: User NOT found")
