from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

from workflows.models.workflow import Workflow


class UserProfile(models.Model):
    user = models.OneToOneField(User, related_name="userprofile")
    active_workflow = models.ForeignKey(Workflow, related_name="users", null=True, blank=True,
                                        on_delete=models.SET_NULL)

    def __unicode__(self):
        return unicode(self.user)


@receiver(post_save, sender=User)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)


def create_user_profile(sender, instance, created, **kwargs):
    profile_set = UserProfile.objects.filter(user__id=instance.id)
    if created and not profile_set.exists():
        UserProfile.objects.create(user=instance)


# nardi da k nardimo userja da se avtomatsko nardi se UserProfile
post_save.connect(create_user_profile, sender=User)