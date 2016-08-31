from rest_framework.reverse import reverse
from rest_framework import status
from rest_framework.test import APITestCase

TEST_USERNAME = 'testuser'
TEST_PASSWORD = '123'
TEST_WORKFLOW_USERS_PK = 3
TEST_WORKFLOW_OTHER_USER_PRIVATE_PK = 4
TEST_WORKFLOW_OTHER_USER_PUBLIC_PK = 6


class APITests(APITestCase):
    fixtures = ['test_data_api', ]

    def _login(self):
        self.client.login(username=TEST_USERNAME, password=TEST_PASSWORD)

    def _logout(self):
        self.client.logout()

    def _test_multiple_response_codes(self, verb, urls, codes, data=None):
        for url, code in zip(urls, codes):
            response = verb(url, data) if data else verb(url)
            self.assertEqual(response.status_code, code)

    def test_widget_library(self):
        """
        Ensure we can get the widget library.
        """
        url = reverse('widget-library-list')

        # Test without authentication - this should fail
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self._login()
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self._logout()

    def test_create_workflow(self):
        url = reverse('workflow-list')

        workflow_data = {
            'name': 'Untitled workflow',
            'is_public': False,
            'description': '',
            'widget': None,
            'template_parent': None
        }

        # Test without authentication - this should not be allowed
        response = self.client.post(url, workflow_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self._login()
        response = self.client.post(url, workflow_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self._logout()

    def test_patch_workflow(self):
        url = reverse('workflow-detail', kwargs={'pk': TEST_WORKFLOW_USERS_PK})
        url_other_user_private = reverse('workflow-detail', kwargs={'pk': TEST_WORKFLOW_OTHER_USER_PRIVATE_PK})
        url_other_user_public = reverse('workflow-detail', kwargs={'pk': TEST_WORKFLOW_OTHER_USER_PUBLIC_PK})

        workflowData = {
            'name': 'Test workflow',
            'is_public': True,
            'description': 'Test description'
        }

        # Test without authentication - this should not be allowed
        response = self.client.patch(url, workflowData, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self._login()
        response = self.client.patch(url, workflowData, format='json')
        updated_workflow = response.data
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(updated_workflow['name'], 'Test workflow')
        self.assertEqual(updated_workflow['is_public'], True)
        self.assertEqual(updated_workflow['description'], 'Test description')

        # Try to patch
        self._test_multiple_response_codes(
            self.client.patch,
            [url_other_user_private, url_other_user_public],
            [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN],
            data=workflowData
        )

        self._logout()

    def test_delete_workflow(self):
        url = reverse('workflow-detail', kwargs={'pk': TEST_WORKFLOW_USERS_PK})
        url_other_user_private = reverse('workflow-detail', kwargs={'pk': TEST_WORKFLOW_OTHER_USER_PRIVATE_PK})
        url_other_user_public = reverse('workflow-detail', kwargs={'pk': TEST_WORKFLOW_OTHER_USER_PUBLIC_PK})

        # Test without authentication - this should not be allowed
        response = self.client.delete(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        self._login()

        self._test_multiple_response_codes(
            self.client.delete,
            [url, url_other_user_private, url_other_user_public],
            [status.HTTP_204_NO_CONTENT, status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN]
        )

        self._logout()

    def test_create_widget(self):
        pass
