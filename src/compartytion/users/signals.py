from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Account, UnauthenticatedUser


@receiver(post_save, sender=Account, dispatch_uid="account_created")
def callback_after_account_created(sender, instance, **kwargs):
    email = instance.email
    UnauthenticatedUser.objects.get(email=email).delete()
