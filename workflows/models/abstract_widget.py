from django.contrib.auth.models import User
from django.db import models

from workflows.models.category import Category
from workflows.thumbs import ThumbnailField


class AbstractWidget(models.Model):
    name = models.CharField(max_length=200,
                            help_text='Name is the name that will be displayed in the widget repository and under the actual widget itself.')
    action = models.CharField(max_length=200,
                              help_text='Action is the name of a python function that will be called when the widget is executed.')
    wsdl = models.URLField(max_length=200, blank=True,
                           help_text='WSDL and WSDL method are used if the widget is a call of a Web Service. Web Service widgets are usually not entered in the admin panel, but in the application itself by importing a Web Service.')
    wsdl_method = models.CharField(max_length=200, blank=True, default='')
    description = models.TextField(blank=True,
                                   help_text='Description is used for a human readable description of what a widget does. A user will see this when he right clicks the widget and clicks help.')
    category = models.ForeignKey(Category, related_name="widgets",
                                 help_text='Category determines to which category this widget belongs. Categories can be nested.')
    visualization_view = models.CharField(max_length=200, blank=True, default='',
                                          help_text='Visualization view is (like the action) a python function that is a view that will render a template.')
    streaming_visualization_view = models.CharField(max_length=200, blank=True, default='',
                                                    help_text='Visualization view is (like the action) a python function that is a view that will render a template.')
    user = models.ForeignKey(User, blank=True, null=True, related_name="widgets",
                             help_text='If the User field is blank, everyone will see the widget, otherwise just this user. This is mainly used for Web Service imports as they are only visible to users that imported them.')
    interactive = models.BooleanField(default=False,
                                      help_text='The widget can be interactive. This means that when a user executes the widget, the action will perform, then the interaction view will be executed and finally the Post interact action will be executed.')
    interaction_view = models.CharField(max_length=200, blank=True, default='')
    post_interact_action = models.CharField(max_length=200, blank=True, default='')

    image = ThumbnailField(blank=True, null=True, upload_to="images", size=(34, 34),
                           help_text='Image and Treeview image are deprecated and will be phased out soon. Please use the static image field.')
    treeview_image = ThumbnailField(blank=True, null=True, upload_to="treeview", size=(16, 16))

    static_image = models.CharField(max_length=250, blank=True, default='',
                                    help_text='In the static image field just enter the filename of the image (without the path). The path will be $package_name$/icons/widget/$filename$ and $package_name$/icons/treeview/$filename$ where the treeview image is the small image that appears in the treeview on the left side and the widget image is the actual normal sized icon for the widget. IMPORTANT: the static image field only works if the package is set.')

    has_progress_bar = models.BooleanField(default=False,
                                           help_text='The flag has progress bar determines if the widget implements a progress bar.')
    is_streaming = models.BooleanField(default=False,
                                       help_text='The is streaming flag is currently under construction, please do not use it yet.')

    order = models.PositiveIntegerField(default=1,
                                        help_text='The Order determines the order in which the widget will be displayed in the repository. This is set automatically when sorting widgets in a single category from the admin.')

    uid = models.CharField(max_length=250, blank=True, default='',
                           help_text='UID is set automatically when you export a package with the -u switch.')

    package = models.CharField(max_length=150, blank=True, default='',
                               help_text='Package is the package name. You are encouraged to use packages.')

    windows_queue = models.BooleanField(default=False, help_text="This is used for Matjaz Jursic's widgets.")

    class Meta:
        ordering = ('order', 'name',)

    def set_uid(self, commit=False):
        import uuid
        self.uid = str(uuid.uuid4())
        if commit:
            self.save()
        for i in self.inputs.all():
            i.uid = str(uuid.uuid4())
            if commit:
                i.save()
            for option in i.options.all():
                option.uid = str(uuid.uuid4())
                if commit:
                    option.save()
        for o in self.outputs.all():
            o.uid = str(uuid.uuid4())
            if commit:
                o.save()

    def update_uid(self):
        import uuid
        if self.uid == '' or self.uid is None:
            self.uid = str(uuid.uuid4())
            self.save()
        for i in self.inputs.filter(uid=''):
            i.uid = str(uuid.uuid4())
            i.save()
            for option in i.options.filter(uid=''):
                option.uid = str(uuid.uuid4())
                option.save()
        for o in self.outputs.filter(uid=''):
            o.uid = str(uuid.uuid4())
            o.save()
        self.category.update_uid()

    def __str__(self):
        return str(self.name)

