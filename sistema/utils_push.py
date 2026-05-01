from django.conf import settings
from .models import PushSubscription
from pywebpush import webpush
import json

def send_push_to_admins(title, body, url='/'):
    # Get all superusers who have subscriptions
    # Or just all subscriptions if we assume only admins access the dashboard code that registers them
    # Better: Filter by user.is_superuser
    subscriptions = PushSubscription.objects.filter(user__is_superuser=True)
    
    payload = json.dumps({
        "title": title,
        "body": body,
        "url": url,
        "icon": "/static/img/logo.png"
    })

    print(f"Sending push to {subscriptions.count()} admins...")

    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {
                        "p256dh": sub.p256dh,
                        "auth": sub.auth
                    }
                },
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={
                    "sub": settings.VAPID_ADMIN_EMAIL
                }
            )
            print("Push sent successfully!")
        except Exception as e:
            print(f"Push failed for {sub.user}: {e}")
            # If 410 Gone, delete subscription
            if "410" in str(e) or "404" in str(e):
                sub.delete()
