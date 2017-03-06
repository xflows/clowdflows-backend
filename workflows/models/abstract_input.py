from django.db import models

class AbstractInput(models.Model):
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=3)
    description = models.TextField(blank=True)
    variable = models.CharField(max_length=50,
                                help_text='The variable attribute of both the input and the output are important because this is how the data will be accessed in the python function that is executed when the widget runs.')
    widget = models.ForeignKey('AbstractWidget', related_name="inputs")
    required = models.BooleanField(default=False)
    parameter = models.BooleanField(default=False)
    multi = models.BooleanField(default=False,
                                help_text='Inputs with this flag set will behave like this: whenever a connection is added to this input another input will be created on the fly that accepts the same data. In the action function, this will be represented as a list.')
    default = models.TextField(blank=True)
    PARAMETER_CHOICES = (
        ('text', 'Single line'),
        ('password', 'Password'),
        ('textarea', 'Multi line text'),
        ('select', 'Select box'),
        ('checkbox', 'Checkbox'),
        ('file', 'File'),
        ('bigfile', 'File'),
    )
    parameter_type = models.CharField(max_length=50, choices=PARAMETER_CHOICES, blank=True, null=True)

    order = models.PositiveIntegerField(default=1)

    uid = models.CharField(max_length=250, blank=True, default='')

    def __unicode__(self):
        return unicode(self.name)

    class Meta:
        ordering = ('order',)
