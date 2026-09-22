from django.contrib.auth.models import Group
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from .models import Rolle
from allauth.account.signals import user_signed_up


@receiver(user_signed_up)
def assign_single_system_learner(sender, request, user, **kwargs):
    from django.conf import settings
    if settings.SINGLE_SYSTEM_MODE:
        from apps.organisations.single_system import system_organisation
        from .models import UserProfile
        UserProfile.objects.get_or_create(nutzer=user, organisation=system_organisation(), rolle=Rolle.LEARNER)


@receiver(post_migrate)
def ensure_role_groups(sender, **kwargs):
    if sender.label != "accounts":
        return
    for role in Rolle:
        Group.objects.get_or_create(name=role.value)
