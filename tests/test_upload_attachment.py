import unittest
from unittest.mock import MagicMock, patch
from io import BytesIO
from src.api import UploadAttachmentCommand, UploadAttachmentCommandInput
from requests.auth import HTTPBasicAuth


class TestUploadAttachmentCommand(unittest.TestCase):
    """Test cases for the UploadAttachmentCommand class."""

    def setUp(self):
        """Set up test fixtures."""
        self.domain = "example.atlassian.net"
        self.page_id = "12345"
        self.filename = "test_image.png"
        self.file_content = BytesIO(b"fake image content")
        self.comment = "Test upload"
        self.auth = HTTPBasicAuth("user@example.com", "api_token")

    def test_upload_attachment_command_input(self):
        """Test UploadAttachmentCommandInput initialization."""
        input_obj = UploadAttachmentCommandInput(
            domain=self.domain,
            page_id=self.page_id,
            filename=self.filename,
            file_content=self.file_content,
            comment=self.comment
        )

        self.assertEqual(input_obj.domain, self.domain)
        self.assertEqual(input_obj.page_id, self.page_id)
        self.assertEqual(input_obj.filename, self.filename)
        self.assertEqual(input_obj.file_content, self.file_content)
        self.assertEqual(input_obj.comment, self.comment)

    def test_upload_attachment_command_input_no_comment(self):
        """Test UploadAttachmentCommandInput without comment."""
        input_obj = UploadAttachmentCommandInput(
            domain=self.domain,
            page_id=self.page_id,
            filename=self.filename,
            file_content=self.file_content
        )

        self.assertIsNone(input_obj.comment)

    @patch('requests.post')
    def test_upload_attachment_command_execute(self, mock_post):
        """Test UploadAttachmentCommand execution."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        input_obj = UploadAttachmentCommandInput(
            domain=self.domain,
            page_id=self.page_id,
            filename=self.filename,
            file_content=self.file_content,
            comment=self.comment
        )

        command = UploadAttachmentCommand(input_obj)
        response = command.execute(self.auth)

        # Verify the API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args

        # Check URL
        self.assertEqual(
            call_args[0][0],
            f"https://{self.domain}/wiki/rest/api/content/{self.page_id}/child/attachment"
        )

        # Check headers
        self.assertEqual(call_args[1]['headers']['X-Atlassian-Token'], 'nocheck')
        self.assertEqual(call_args[1]['headers']['Accept'], 'application/json')

        # Check files
        self.assertIn('files', call_args[1])
        self.assertIn('file', call_args[1]['files'])

        # Check data
        self.assertIn('data', call_args[1])
        self.assertEqual(call_args[1]['data']['comment'], self.comment)

        # Check auth
        self.assertEqual(call_args[1]['auth'], self.auth)

        # Check response
        self.assertEqual(response, mock_response)

    @patch('requests.post')
    def test_upload_attachment_command_execute_no_comment(self, mock_post):
        """Test UploadAttachmentCommand execution without comment."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response

        input_obj = UploadAttachmentCommandInput(
            domain=self.domain,
            page_id=self.page_id,
            filename=self.filename,
            file_content=self.file_content
        )

        command = UploadAttachmentCommand(input_obj)
        response = command.execute(self.auth)

        # Verify the API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args

        # Check data doesn't contain comment
        self.assertEqual(call_args[1]['data'], {})

        # Check response
        self.assertEqual(response.status_code, 201)

    @patch('requests.post')
    def test_upload_attachment_command_failure(self, mock_post):
        """Test handling of upload failure."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_post.return_value = mock_response

        input_obj = UploadAttachmentCommandInput(
            domain=self.domain,
            page_id=self.page_id,
            filename=self.filename,
            file_content=self.file_content
        )

        command = UploadAttachmentCommand(input_obj)
        response = command.execute(self.auth)

        self.assertEqual(response.status_code, 403)


if __name__ == '__main__':
    unittest.main()