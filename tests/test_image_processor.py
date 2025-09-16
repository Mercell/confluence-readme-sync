import unittest
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path
from src.image_processor import ImageProcessor


class TestImageProcessor(unittest.TestCase):
    """Test cases for the ImageProcessor class."""

    def setUp(self):
        """Set up test fixtures."""
        self.processor = ImageProcessor(base_path="/test/path")

    def test_extract_images(self):
        """Test extracting image references from markdown."""
        markdown = """
        # Test Document
        Here is an image: ![Alt text](image.png)
        Another one: ![Description](https://example.com/image.jpg)
        And one more: ![](./relative/path.gif)
        """

        images = self.processor.extract_images(markdown)

        self.assertEqual(len(images), 3)
        self.assertEqual(images[0], ('![Alt text](image.png)', 'Alt text', 'image.png'))
        self.assertEqual(images[1], ('![Description](https://example.com/image.jpg)', 'Description', 'https://example.com/image.jpg'))
        self.assertEqual(images[2], ('![](./relative/path.gif)', '', './relative/path.gif'))

    def test_is_local_path(self):
        """Test identifying local vs remote paths."""
        # Local paths
        self.assertTrue(self.processor.is_local_path('image.png'))
        self.assertTrue(self.processor.is_local_path('./images/photo.jpg'))
        self.assertTrue(self.processor.is_local_path('../assets/diagram.svg'))
        self.assertTrue(self.processor.is_local_path('/absolute/path/file.gif'))

        # Remote URLs
        self.assertFalse(self.processor.is_local_path('http://example.com/image.png'))
        self.assertFalse(self.processor.is_local_path('https://example.com/image.png'))
        self.assertFalse(self.processor.is_local_path('ftp://server.com/file.jpg'))

    def test_resolve_image_path(self):
        """Test resolving relative and absolute paths."""
        processor = ImageProcessor(base_path="/project/docs")

        # Relative path
        resolved = processor.resolve_image_path("images/diagram.png")
        self.assertEqual(resolved, Path("/project/docs/images/diagram.png"))

        # Absolute path
        resolved = processor.resolve_image_path("/absolute/path/image.jpg")
        self.assertEqual(resolved, Path("/absolute/path/image.jpg"))

    def test_get_filename_from_path(self):
        """Test extracting filename from path."""
        self.assertEqual(self.processor.get_filename_from_path('image.png'), 'image.png')
        self.assertEqual(self.processor.get_filename_from_path('./images/photo.jpg'), 'photo.jpg')
        self.assertEqual(self.processor.get_filename_from_path('/absolute/path/file.gif'), 'file.gif')

    @patch('pathlib.Path.exists')
    def test_process_markdown_images(self, mock_exists):
        """Test processing markdown to identify and prepare images for upload."""
        mock_exists.return_value = True

        markdown = """
        # Document with Images
        Local image: ![Local](./images/local.png)
        Remote image: ![Remote](https://example.com/remote.jpg)
        Another local: ![Another](../assets/diagram.svg)
        """

        modified_md, images_to_upload = self.processor.process_markdown_images(markdown)

        # Check that local images are marked for upload
        self.assertEqual(len(images_to_upload), 2)
        self.assertEqual(images_to_upload[0]['filename'], 'local.png')
        self.assertEqual(images_to_upload[1]['filename'], 'diagram.svg')

        # Check that markdown is modified with confluence-attachment placeholders
        self.assertIn('![Local](confluence-attachment:local.png)', modified_md)
        self.assertIn('![Another](confluence-attachment:diagram.svg)', modified_md)

        # Remote images should remain unchanged
        self.assertIn('![Remote](https://example.com/remote.jpg)', modified_md)

    @patch('pathlib.Path.exists')
    def test_process_markdown_images_missing_file(self, mock_exists):
        """Test handling of missing image files."""
        mock_exists.return_value = False

        markdown = "![Missing](./missing.png)"

        with patch('logging.warning') as mock_warning:
            modified_md, images_to_upload = self.processor.process_markdown_images(markdown)

            # No images should be uploaded
            self.assertEqual(len(images_to_upload), 0)

            # Original markdown should be unchanged
            self.assertEqual(modified_md, markdown)

            # Warnings should be logged (multiple calls for missing file message and paths tried)
            self.assertTrue(mock_warning.called)
            # Check that at least one warning mentions the missing file
            warning_messages = [str(call[0][0]) for call in mock_warning.call_args_list]
            self.assertTrue(any('Image file not found' in msg or 'missing.png' in msg for msg in warning_messages))

    def test_mark_as_uploaded(self):
        """Test marking images as uploaded."""
        self.processor.mark_as_uploaded('/path/to/image.png', 'image.png')

        self.assertIn('/path/to/image.png', self.processor.uploaded_attachments)
        self.assertEqual(self.processor.uploaded_attachments['/path/to/image.png'], 'image.png')

    @patch('pathlib.Path.exists')
    def test_avoid_duplicate_uploads(self, mock_exists):
        """Test that already uploaded images are not marked for re-upload."""
        mock_exists.return_value = True

        # Mark an image as already uploaded
        self.processor.mark_as_uploaded('/test/path/images/local.png', 'local.png')

        markdown = "![Local](./images/local.png)"

        modified_md, images_to_upload = self.processor.process_markdown_images(markdown)

        # Image should not be in upload list since it's already uploaded
        self.assertEqual(len(images_to_upload), 0)

        # But markdown should still be modified
        self.assertIn('![Local](confluence-attachment:local.png)', modified_md)


if __name__ == '__main__':
    unittest.main()