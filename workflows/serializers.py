import json
from django.contrib.auth.models import User
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
    # options = AbstractOptionSerializer(many=True, read_only=True)
    class Meta:
        model = AbstractInput
        fields = (
            'name', 'short_name', 'description', 'variable', 'required', 'parameter', 'multi', 'default',
            'parameter_type',
            'order',)  # 'options')
        read_only_fields = (
            'name', 'short_name', 'description', 'variable', 'required', 'parameter', 'multi', 'default',
            'parameter_type',
            'order',)  # 'options')


class AbstractOutputSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = AbstractOutput
        fields = ('name', 'short_name', 'description', 'variable', 'order')
        read_only_fields = ('name', 'short_name', 'description', 'variable', 'order')


class AbstractWidgetSerializer(serializers.HyperlinkedModelSerializer):
    inputs = AbstractInputSerializer(many=True, read_only=True)
    outputs = AbstractOutputSerializer(many=True, read_only=True)

    class Meta:
        model = AbstractWidget
        fields = ('name', 'interactive', 'static_image', 'order', 'outputs', 'inputs')
        read_only_fields = ('name', 'interactive', 'static_image', 'order', 'outputs', 'inputs')


class CategorySerializer(serializers.HyperlinkedModelSerializer):
    widgets = AbstractWidgetSerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ('name', 'user', 'order', 'children', 'widgets')
        read_only_fields = ('name', 'user', 'order', 'children', 'widgets')


CategorySerializer._declared_fields['children'] = CategorySerializer(many=True, read_only=True)


class ConnectionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Connection


class InputSerializer(serializers.HyperlinkedModelSerializer):
    deserialized_value = serializers.SerializerMethodField()

    def get_deserialized_value(self, obj):
        try:
            json.dumps(obj.value)
        except:
            return repr(obj.value)
        else:
            return obj.value

    class Meta:
        model = Input
        exclude = ('value',)


class OutputSerializer(serializers.HyperlinkedModelSerializer):
    deserialized_value = serializers.SerializerMethodField()

    def get_deserialized_value(self, obj):
        try:
            json.dumps(obj.value)
        except:
            return repr(obj.value)
        else:
            return obj.value

    class Meta:
        model = Output
        exclude = ('value',)


class WidgetListSerializer(serializers.HyperlinkedModelSerializer):
    abstract_widget = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Widget
        # exclude = ('abstract_widget',)


class WorkflowListSerializer(serializers.HyperlinkedModelSerializer):
    is_subprocess = serializers.SerializerMethodField()

    def get_is_subprocess(self, obj):
        if obj.widget == None:
            return False
        else:
            return True

    class Meta:
        model = Workflow
        exclude = ('user',)


class WidgetSerializer(serializers.HyperlinkedModelSerializer):
    inputs = InputSerializer(many=True, read_only=True)
    outputs = OutputSerializer(many=True, read_only=True)
    workflow_link = serializers.HyperlinkedRelatedField(
        read_only=True,
        view_name='workflow-detail'
    )
    abstract_widget = serializers.PrimaryKeyRelatedField(queryset=AbstractWidget.objects.all())

    class Meta:
        model = Widget
        # exclude = ('abstract_widget',)


class WorkflowSerializer(serializers.HyperlinkedModelSerializer):
    widgets = WidgetSerializer(many=True, read_only=True)
    connections = ConnectionSerializer(many=True, read_only=True)
    is_subprocess = serializers.SerializerMethodField()

    def get_is_subprocess(self, obj):
        if obj.widget == None:
            return False
        else:
            return True

    class Meta:
        model = Workflow
        exclude = ('user',)
