from django.db import models

class StoreSettings(models.Model):
    is_open = models.BooleanField(default=True)
    
    def save(self, *args, **kwargs):
        if not self.pk and StoreSettings.objects.exists():
            # If you try to save a new instance but one exists, update the existing one
            return StoreSettings.objects.first().save(*args, **kwargs)
        return super(StoreSettings, self).save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f"Store is {'Open' if self.is_open else 'Closed'}"
