from django.contrib.auth.models import User
from rest_framework.reverse import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from workflows.models import Workflow, Widget, Input

TEST_USERNAME = 'testuser'
TEST_PASSWORD = '123'

# Test workflow ids
TEST_WORKFLOW_USERS_PK = 2
TEST_WORKFLOW_OTHER_USER_PRIVATE_PK = 4
TEST_WORKFLOW_OTHER_USER_PUBLIC_PK = 6
TEST_OUTPUT_PK = 9

# Test widget ids
TEST_WIDGET_USERS_PK = 6
TEST_WIDGET_OTHER_USER_PRIVATE_PK = 33
TEST_WIDGET_OTHER_USER_PUBLIC_PK = 34

# Test widget parameters
TEST_PARAMETER_USERS_PK = 10
TEST_PARAMETER_OTHER_USER_PRIVATE_PK = 98
TEST_PARAMETER_OTHER_USER_PUBLIC_PK = 99


class BaseAPITestCase(APITestCase):
    fixtures = ['test_data_api', ]

    def _login(self):
        self.client.login(username=TEST_USERNAME, password=TEST_PASSWORD)

    def _logout(self):
        self.client.logout()

    def _test_multiple_response_codes(self, verb, urls, codes, data=None):
        for url, code in zip(urls, codes):
            response = verb(url, data) if data else verb(url)
            self.assertEqual(response.status_code, code)


class SupportingAPITests(BaseAPITestCase):
    def test_register(self):
        url = reverse('user-create')
        response = self.client.post(url, {
            'username': 'testuser3',
            'password': '123',
            'email': 'testuser3@testdomain.com'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(username='testuser3').count(), 1)

    def test_login(self):
        url = reverse('token-create')
        response = self.client.post(url, {
            'username': 'testuser',
            'password': '123'
        })
        self.assertEqual(response.status_code, 200)

    def test_logout(self):
        url = reverse('token-destroy')
        self._login()
        response = self.client.post(url) # HTTP_AUTHORIZATION="Token %s" % auth_token)
        self.assertEqual(response.status_code, 204)

    def test_widget_library(self):
        url = reverse('widget-library-list')

        # Test without authentication - this should fail
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self._login()
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self._logout()


class WorkflowAPITests(BaseAPITestCase):
    def test_create(self):
        url = reverse('workflow-list')

        workflow_data = {
            'name': 'Untitled workflow',
            'is_public': False,
            'description': '',
            'widget': None,
            'template_parent': None
        }

        # Test without authentication - this should not be allowed
        response = self.client.post(url, workflow_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self._login()
        response = self.client.post(url, workflow_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self._logout()

    def test_patch(self):
        url = reverse('workflow-detail', kwargs={'pk': TEST_WORKFLOW_USERS_PK})
        url_other_user_private = reverse('workflow-detail', kwargs={'pk': TEST_WORKFLOW_OTHER_USER_PRIVATE_PK})
        url_other_user_public = reverse('workflow-detail', kwargs={'pk': TEST_WORKFLOW_OTHER_USER_PUBLIC_PK})

        workflowData = {
            'name': 'Test workflow',
            'is_public': True,
            'description': 'Test description'
        }

        # Test without authentication - this should not be allowed
        response = self.client.patch(url, workflowData)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self._login()
        response = self.client.patch(url, workflowData)
        updated_workflow = response.data
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(updated_workflow['name'], 'Test workflow')
        self.assertEqual(updated_workflow['is_public'], True)
        self.assertEqual(updated_workflow['description'], 'Test description')

        # Try to patch
        self._test_multiple_response_codes(
            self.client.patch,
            [url_other_user_private, url_other_user_public],
            [status.HTTP_403_FORBIDDEN, status.HTTP_403_FORBIDDEN],
            data=workflowData
        )

        self._logout()

    def test_delete(self):
        url = reverse('workflow-detail', kwargs={'pk': TEST_WORKFLOW_USERS_PK})
        url_other_user_private = reverse('workflow-detail', kwargs={'pk': TEST_WORKFLOW_OTHER_USER_PRIVATE_PK})
        url_other_user_public = reverse('workflow-detail', kwargs={'pk': TEST_WORKFLOW_OTHER_USER_PUBLIC_PK})

        # Test without authentication - this should not be allowed
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self._login()

        self._test_multiple_response_codes(
            self.client.delete,
            [url, url_other_user_private, url_other_user_public],
            [status.HTTP_204_NO_CONTENT, status.HTTP_403_FORBIDDEN, status.HTTP_403_FORBIDDEN]
        )

        self._logout()

    def test_reset(self):
        url = reverse('workflow-reset', kwargs={'pk': TEST_WORKFLOW_USERS_PK})
        url_other_user_private = reverse('workflow-reset', kwargs={'pk': TEST_WORKFLOW_OTHER_USER_PRIVATE_PK})
        url_other_user_public = reverse('workflow-reset', kwargs={'pk': TEST_WORKFLOW_OTHER_USER_PUBLIC_PK})

        # Test without authentication - this should not be allowed
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self._login()

        response = self.client.post(url, format="json")
        data = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(data['status'], 'ok')

        workflow = Workflow.objects.get(pk=TEST_WORKFLOW_USERS_PK)
        for widget in workflow.widgets.all():
            self.assertEqual(widget.finished, False)
            self.assertEqual(widget.error, False)
            self.assertEqual(widget.running, False)

        self._test_multiple_response_codes(
            self.client.post,
            [url_other_user_private, url_other_user_public],
            [status.HTTP_403_FORBIDDEN, status.HTTP_403_FORBIDDEN]
        )

        self._logout()

    def test_run(self):
        url = reverse('workflow-run', kwargs={'pk': TEST_WORKFLOW_USERS_PK})
        url_other_user_private = reverse('workflow-run', kwargs={'pk': TEST_WORKFLOW_OTHER_USER_PRIVATE_PK})
        url_other_user_public = reverse('workflow-run', kwargs={'pk': TEST_WORKFLOW_OTHER_USER_PUBLIC_PK})

        # Test without authentication - this should not be allowed
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self._login()

        response = self.client.post(url, format="json")
        # data = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # self.assertEqual(data['status'], 'ok')

        workflow = Workflow.objects.get(pk=TEST_WORKFLOW_USERS_PK)
        for widget in workflow.widgets.all():
            self.assertEqual(widget.finished, True)

        self._test_multiple_response_codes(
            self.client.post,
            [url_other_user_private, url_other_user_public],
            [status.HTTP_403_FORBIDDEN, status.HTTP_403_FORBIDDEN]
        )

        self._logout()

    def test_subprocess(self):
        url = reverse('workflow-subprocess', kwargs={'pk': TEST_WORKFLOW_USERS_PK})
        url_other_user_private = reverse('workflow-subprocess', kwargs={'pk': TEST_WORKFLOW_OTHER_USER_PRIVATE_PK})
        url_other_user_public = reverse('workflow-subprocess', kwargs={'pk': TEST_WORKFLOW_OTHER_USER_PUBLIC_PK})

        # Test without authentication - this should not be allowed
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self._login()

        response = self.client.post(url, format="json")
        widget = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(widget['type'], 'subprocess')

        self._test_multiple_response_codes(
            self.client.post,
            [url_other_user_private, url_other_user_public],
            [status.HTTP_403_FORBIDDEN, status.HTTP_403_FORBIDDEN]
        )

        # Get subprocess workflow object
        subprocess_workflow = Widget.objects.get(pk=widget['id']).workflow_link

        # Test adding input
        url = reverse('workflow-subprocess-input', kwargs={'pk': subprocess_workflow.pk})
        response = self.client.post(url)
        widget = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(widget['type'], 'input')

        # Test adding output
        url = reverse('workflow-subprocess-output', kwargs={'pk': subprocess_workflow.pk})
        response = self.client.post(url)
        widget = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(widget['type'], 'output')

        self._logout()

    def test_subprocess_forloop(self):
        url = reverse('workflow-subprocess', kwargs={'pk': TEST_WORKFLOW_USERS_PK})

        self._login()

        # First add a subprocess
        response = self.client.post(url)
        widget = response.json()
        subprocess_workflow = Widget.objects.get(pk=widget['id']).workflow_link

        # Test adding for loop widgets
        url = reverse('workflow-subprocess-forloop', kwargs={'pk': subprocess_workflow.pk})
        response = self.client.post(url)
        data = response.json()
        self.assertNotIn('status', data)
        widget_types = {w['type'] for w in data}
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertSetEqual(widget_types, {'for_input', 'for_output'})

        self._logout()

    def test_subprocess_xvalidation(self):
        url = reverse('workflow-subprocess', kwargs={'pk': TEST_WORKFLOW_USERS_PK})

        self._login()

        # First add a subprocess
        response = self.client.post(url)
        data = response.json()
        self.assertNotIn('status', data)
        subprocess_workflow = Widget.objects.get(pk=data['id']).workflow_link

        # Test adding cross validation widgets
        url = reverse('workflow-subprocess-xvalidation', kwargs={'pk': subprocess_workflow.pk})
        response = self.client.post(url)
        widgets = response.json()
        widget_types = {w['type'] for w in widgets}
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertSetEqual(widget_types, {'cv_input', 'cv_output'})

        self._logout()


class WidgetAPITests(BaseAPITestCase):
    def test_fetch_value(self):
        url = reverse('output-value', kwargs={'pk': TEST_OUTPUT_PK})
        self._login()
        response = self.client.get(url)
        data = response.json()
        self.assertEqual(data['value'], '5')

    def test_create(self):
        url = reverse('widget-list')
        workflow_url = reverse('workflow-detail', kwargs={'pk': TEST_WORKFLOW_USERS_PK})
        workflow_url_private = reverse('workflow-detail', kwargs={'pk': TEST_WORKFLOW_OTHER_USER_PRIVATE_PK})
        workflow_url_public = reverse('workflow-detail', kwargs={'pk': TEST_WORKFLOW_OTHER_USER_PUBLIC_PK})

        widget_data = {
            'workflow': workflow_url,
            'x': 50,
            'y': 50,
            'name': 'Test widget',
            'abstract_widget': 3,  # Multiply integers abstract widget
            'finished': False,
            'error': False,
            'running': False,
            'interaction_waiting': False,
            'type': 'regular',
            'progress': 0
        }

        # Test without authentication - this should not be allowed
        response = self.client.post(url, widget_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self._login()
        response = self.client.post(url, widget_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Test on other user's workflows
        widget_data['workflow'] = workflow_url_private
        response = self.client.post(url, widget_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        widget_data['workflow'] = workflow_url_public
        response = self.client.post(url, widget_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self._logout()

    def test_patch(self):
        widget_url = reverse('widget-detail', kwargs={'pk': TEST_WIDGET_USERS_PK})
        widget_url_private = reverse('widget-detail', kwargs={'pk': TEST_WIDGET_OTHER_USER_PRIVATE_PK})
        widget_url_public = reverse('widget-detail', kwargs={'pk': TEST_WIDGET_OTHER_USER_PUBLIC_PK})

        widget_data = {
            'x': 12,
            'y': 34,
            'name': 'Test name'
        }

        # Test without authentication - this should not be allowed
        response = self.client.patch(widget_url, widget_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self._login()
        response = self.client.patch(widget_url, widget_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        widget = Widget.objects.get(pk=TEST_WIDGET_USERS_PK)
        self.assertEqual(widget.x, widget_data['x'])
        self.assertEqual(widget.y, widget_data['y'])
        self.assertEqual(widget.name, widget_data['name'])

        # Test on other user's widgets
        response = self.client.patch(widget_url_private, widget_data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self.client.patch(widget_url_public, widget_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self._logout()

    def test_reset(self):
        widget_url = reverse('widget-reset', kwargs={'pk': TEST_WIDGET_USERS_PK})
        widget_url_private = reverse('widget-reset', kwargs={'pk': TEST_WIDGET_OTHER_USER_PRIVATE_PK})
        widget_url_public = reverse('widget-reset', kwargs={'pk': TEST_WIDGET_OTHER_USER_PUBLIC_PK})

        # Test without authentication - this should not be allowed
        response = self.client.post(widget_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self._login()
        response = self.client.post(widget_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        widget = Widget.objects.get(pk=TEST_WIDGET_USERS_PK)
        self.assertEqual(widget.finished, False)

        # Test on other user's widgets
        response = self.client.post(widget_url_private)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self.client.post(widget_url_public)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self._logout()

    def test_run(self):
        widget_url = reverse('widget-run', kwargs={'pk': TEST_WIDGET_USERS_PK})
        widget_reset_url = reverse('widget-reset', kwargs={'pk': TEST_WIDGET_USERS_PK})
        widget_url_private = reverse('widget-run', kwargs={'pk': TEST_WIDGET_OTHER_USER_PRIVATE_PK})
        widget_url_public = reverse('widget-run', kwargs={'pk': TEST_WIDGET_OTHER_USER_PUBLIC_PK})

        # Test without authentication - this should not be allowed
        response = self.client.post(widget_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self._login()
        # First reset the widget
        response = self.client.post(widget_reset_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        widget = Widget.objects.get(pk=TEST_WIDGET_USERS_PK)
        self.assertEqual(widget.finished, False)

        # .. then run
        response = self.client.post(widget_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        widget = Widget.objects.get(pk=TEST_WIDGET_USERS_PK)
        self.assertEqual(widget.finished, True)

        # Test on other user's widgets
        response = self.client.post(widget_url_private)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self.client.post(widget_url_public)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self._logout()

    def test_delete(self):
        widget_url = reverse('widget-detail', kwargs={'pk': TEST_WIDGET_USERS_PK})
        widget_url_private = reverse('widget-detail', kwargs={'pk': TEST_WIDGET_OTHER_USER_PRIVATE_PK})
        widget_url_public = reverse('widget-detail', kwargs={'pk': TEST_WIDGET_OTHER_USER_PUBLIC_PK})

        # Test without authentication - this should not be allowed
        response = self.client.delete(widget_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self._login()
        response = self.client.delete(widget_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        widget_count = Widget.objects.filter(pk=TEST_WIDGET_USERS_PK).count()
        self.assertEqual(widget_count, 0)

        # Test on other user's widgets
        response = self.client.delete(widget_url_private)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self.client.delete(widget_url_public)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self._logout()

    def test_save_parameters(self):
        widget_url = reverse('widget-save-parameters', kwargs={'pk': TEST_WIDGET_USERS_PK})
        widget_url_private = reverse('widget-save-parameters', kwargs={'pk': TEST_WIDGET_OTHER_USER_PRIVATE_PK})
        widget_url_public = reverse('widget-save-parameters', kwargs={'pk': TEST_WIDGET_OTHER_USER_PUBLIC_PK})

        parameters = [{
            'id': TEST_PARAMETER_USERS_PK,
            'value': '42'
        }]

        # Test without authentication - this should not be allowed
        response = self.client.patch(widget_url, parameters)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self._login()
        response = self.client.patch(widget_url, parameters)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        parameter = Input.objects.get(pk=TEST_PARAMETER_USERS_PK)
        self.assertEqual(parameter.value, '42')

        # Test on other user's widgets
        parameters[0]['id'] = TEST_PARAMETER_OTHER_USER_PRIVATE_PK
        response = self.client.patch(widget_url_private, parameters)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        parameters[0]['id'] = TEST_PARAMETER_OTHER_USER_PUBLIC_PK
        response = self.client.patch(widget_url_public, parameters)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self._logout()
