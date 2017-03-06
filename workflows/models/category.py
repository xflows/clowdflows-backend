from django.contrib.auth.models import User
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=50)
    parent = models.ForeignKey('self', related_name="children", null=True, blank=True)
    user = models.ForeignKey(User, null=True, blank=True, related_name="categories")

    workflow = models.ForeignKey('Workflow', null=True, blank=True, related_name="categories")

    order = models.PositiveIntegerField(default=1)

    uid = models.CharField(max_length=250, blank=True, default='')

    def update_uid(self):
        import uuid
        if self.uid == '' or self.uid is None:
            self.uid = str(uuid.uuid4())
            self.save()
        if self.parent:
            self.parent.update_uid()

    class Meta:
        verbose_name_plural = "categories"
        ordering = ('order', 'name',)

    def __unicode__(self):
        if self.parent is None:
            return unicode(self.name)
        else:
            return unicode(unicode(self.parent) + " :: " + self.name)

