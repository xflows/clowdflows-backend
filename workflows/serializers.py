from rest_framework import serializers
from workflows.models import *


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('username',)


class AbstractOptionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = AbstractOption
        fields = ('name', 'value')
        read_only_fields = ('name', 'value')


class AbstractInputSerializer(serializers.HyperlinkedModelSerializer):
    options = AbstractOptionSerializer(many=True, read_only=True)

    class Meta:
        model = AbstractInput
        fields = (
            'name', 'short_name', 'description', 'variable', 'required', 'parameter', 'multi', 'default',
            'parameter_type',
            'order', 'options')
        read_only_fields = (
            'name', 'short_name', 'description', 'variable', 'required', 'parameter', 'multi', 'default',
            'parameter_type',
            'order', 'options')


class AbstractOutputSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = AbstractOutput
        fields = ('name', 'short_name', 'description', 'variable', 'order')
        read_only_fields = ('name', 'short_name', 'description', 'variable', 'order')


class AbstractWidgetSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField()
    inputs = AbstractInputSerializer(many=True, read_only=True)
    outputs = AbstractOutputSerializer(many=True, read_only=True)
    cfpackage = serializers.SerializerMethodField()

    def get_cfpackage(self, obj):
        return obj.package

    class Meta:
        model = AbstractWidget
        fields = ('id', 'name', 'interactive', 'static_image', 'order', 'outputs', 'inputs', 'cfpackage')
        read_only_fields = ('id', 'name', 'interactive', 'static_image', 'order', 'outputs', 'inputs', 'cfpackage')


class CategorySerializer(serializers.HyperlinkedModelSerializer):
    widgets = AbstractWidgetSerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ('name', 'user', 'order', 'children', 'widgets')
        read_only_fields = ('name', 'user', 'order', 'children', 'widgets')


CategorySerializer._declared_fields['children'] = CategorySerializer(many=True, read_only=True)


class ConnectionSerializer(serializers.HyperlinkedModelSerializer):
    output_widget = serializers.SerializerMethodField()
    input_widget = serializers.SerializerMethodField()

    def get_output_widget(self, obj):
        return WidgetListSerializer(obj.output.widget, context=self.context).data["url"]

    def get_input_widget(self, obj):
        return WidgetListSerializer(obj.input.widget, context=self.context).data["url"]

    class Meta:
        model = Connection


class OptionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Option
        fields = ('name', 'value')


class InputSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    deserialized_value = serializers.SerializerMethodField()
    options = OptionSerializer(many=True, read_only=True)

    def get_deserialized_value(self, obj):
        if obj.parameter:
            try:
                json.dumps(obj.value)
            except:
                return repr(obj.value)
            else:
                return obj.value
        else:
            return ''

    class Meta:
        model = Input
        exclude = ('value',)
        read_only_fields = ('id', 'url', 'widget')


class OutputSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Output
        exclude = ('value',)
        read_only_fields = ('id', 'url', 'widget')


class WorkflowListSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    is_subprocess = serializers.SerializerMethodField()
    is_public = serializers.BooleanField(source='public')

    def get_is_subprocess(self, obj):
        if obj.widget == None:
            return False
        else:
            return True

    class Meta:
        model = Workflow
        exclude = ('user', 'public')


class WidgetSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    inputs = InputSerializer(many=True, read_only=True)
    outputs = OutputSerializer(many=True, read_only=True)
    description = serializers.CharField(source='abstract_widget.description', read_only=True)
    icon = serializers.SerializerMethodField()

    workflow_link = serializers.HyperlinkedRelatedField(
        read_only=True,
        view_name='workflow-detail'
    )
    abstract_widget = serializers.PrimaryKeyRelatedField(queryset=AbstractWidget.objects.all())

    def create(self, validated_data):
        '''
        Overrides the default create method to support nested creates
        '''
        w = Widget.objects.create(**validated_data)
        aw = w.abstract_widget
        input_order, param_order = 0, 0
        for i in aw.inputs.all():
            j = Input()
            j.name = i.name
            j.short_name = i.short_name
            j.description = i.description
            j.variable = i.variable
            j.widget = w
            j.required = i.required
            j.parameter = i.parameter
            j.value = None
            if (i.parameter):
                param_order += 1
                j.order = param_order
            else:
                input_order += 1
                j.order = input_order
            if not i.multi:
                j.value = i.default
            j.parameter_type = i.parameter_type
            if i.multi:
                j.multi_id = i.id
            j.save()
            for k in i.options.all():
                o = Option()
                o.name = k.name
                o.value = k.value
                o.input = j
                o.save()
        outputOrder = 0
        for i in aw.outputs.all():
            j = Output()
            j.name = i.name
            j.short_name = i.short_name
            j.description = i.description
            j.variable = i.variable
            j.widget = w
            outputOrder += 1
            j.order = outputOrder
            j.save()
        w.defered_outputs = w.outputs.defer("value").all()
        w.defered_inputs = w.inputs.defer("value").all()
        return w

    def update(self, widget, validated_data):
        '''
        Overrides the default update method to support nested creates
        '''
        # Ignore inputs and outputs on patch - we allow only nested creates
        if 'inputs' in validated_data:
            validated_data.pop('inputs')
        if 'outputs' in validated_data:
            validated_data.pop('outputs')
        widget, _ = Widget.objects.update_or_create(pk=widget.pk, defaults=validated_data)
        return widget

    def get_icon(self, widget):
        full_path_tokens = self.context['request'].build_absolute_uri().split('/')
        protocol = full_path_tokens[0]
        base_url = full_path_tokens[2]
        icon_path = 'widget-icons/question-mark.png'
        static_or_media = settings.STATIC_URL
        if widget.abstract_widget:
            if widget.abstract_widget.static_image:
                icon_path = '{}/icons/widget/{}'.format(widget.abstract_widget.package, widget.abstract_widget.static_image)
            elif widget.abstract_widget.image:
                static_or_media = settings.MEDIA_URL
                icon_path = widget.abstract_widget.image
            elif widget.abstract_widget.wsdl:
                icon_path = 'widget-icons/ws.png'
        elif hasattr(widget, 'workflow_link'):
            icon_path = 'images/120px-Gears_icon.png'
        elif widget.type == 'input':
            icon_path = 'images/forward-arrow.png'
        elif widget.type == 'output':
            icon_path = 'images/forward-arrow.png'
        elif widget.type == 'output':
            icon_path = 'images/Toolbar_-_Loop.png'
        icon_url = '{}//{}{}{}'.format(protocol, base_url, static_or_media, icon_path)
        return icon_url

    class Meta:
        model = Widget
        fields = (
            'id', 'url', 'workflow', 'x', 'y', 'name', 'abstract_widget', 'finished', 'error', 'running',
            'interaction_waiting', 'description', 'icon',
            'type', 'progress', 'inputs', 'outputs', 'workflow_link')


class WidgetPositionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Widget
        fields = ('x', 'y')


class WidgetListSerializer(serializers.HyperlinkedModelSerializer):
    abstract_widget = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Widget
        # exclude = ('abstract_widget',)


class WorkflowSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    widgets = WidgetSerializer(many=True, read_only=True)
    connections = ConnectionSerializer(many=True, read_only=True)
    is_subprocess = serializers.SerializerMethodField()
    is_public = serializers.BooleanField(source='public')

    def get_is_subprocess(self, obj):
        if obj.widget == None:
            return False
        else:
            return True

    class Meta:
        model = Workflow
        exclude = ('user', 'public',)
