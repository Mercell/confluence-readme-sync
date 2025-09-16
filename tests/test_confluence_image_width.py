import unittest
from src.confluence_markdown_extension import ImagePreprocessor, ConfluenceExtension
from markdown import Markdown


class TestImageWidthConfiguration(unittest.TestCase):
    """Test cases for image width configuration in Confluence markdown extension."""

    def test_image_preprocessor_with_width(self):
        """Test ImagePreprocessor with max_width set."""
        md = Markdown()
        processor = ImagePreprocessor(md, max_width="600")

        lines = ['![Test Image](confluence-attachment:test.png)']
        result = processor.run(lines)

        expected = '<ac:image ac:alt="Test Image" ac:width="600"><ri:attachment ri:filename="test.png" /></ac:image>'
        self.assertEqual(result[0], expected)

    def test_image_preprocessor_without_width(self):
        """Test ImagePreprocessor without max_width."""
        md = Markdown()
        processor = ImagePreprocessor(md, max_width=None)

        lines = ['![Test Image](confluence-attachment:test.png)']
        result = processor.run(lines)

        expected = '<ac:image ac:alt="Test Image"><ri:attachment ri:filename="test.png" /></ac:image>'
        self.assertEqual(result[0], expected)

    def test_image_preprocessor_with_zero_width(self):
        """Test ImagePreprocessor with max_width set to '0'."""
        md = Markdown()
        processor = ImagePreprocessor(md, max_width="0")

        lines = ['![Test Image](confluence-attachment:test.png)']
        result = processor.run(lines)

        expected = '<ac:image ac:alt="Test Image"><ri:attachment ri:filename="test.png" /></ac:image>'
        self.assertEqual(result[0], expected)

    def test_image_preprocessor_with_empty_width(self):
        """Test ImagePreprocessor with max_width set to empty string."""
        md = Markdown()
        processor = ImagePreprocessor(md, max_width="")

        lines = ['![Test Image](confluence-attachment:test.png)']
        result = processor.run(lines)

        expected = '<ac:image ac:alt="Test Image"><ri:attachment ri:filename="test.png" /></ac:image>'
        self.assertEqual(result[0], expected)

    def test_confluence_extension_with_max_width(self):
        """Test ConfluenceExtension with max_image_width configuration."""
        md_text = '![Test Image](confluence-attachment:test.png)'

        # Test with max_image_width set
        extension = ConfluenceExtension(max_image_width="500")
        md = Markdown(extensions=[extension])
        result = md.convert(md_text)

        self.assertIn('ac:width="500"', result)

    def test_confluence_extension_without_max_width(self):
        """Test ConfluenceExtension without max_image_width configuration."""
        md_text = '![Test Image](confluence-attachment:test.png)'

        # Test without max_image_width
        extension = ConfluenceExtension()
        md = Markdown(extensions=[extension])
        result = md.convert(md_text)

        self.assertNotIn('ac:width', result)

    def test_multiple_images_with_width(self):
        """Test multiple images with width setting."""
        md = Markdown()
        processor = ImagePreprocessor(md, max_width="700")

        lines = [
            'Some text here',
            '![First Image](confluence-attachment:first.png)',
            'More text',
            '![Second Image](confluence-attachment:second.jpg)'
        ]
        result = processor.run(lines)

        self.assertEqual(result[0], 'Some text here')
        self.assertIn('ac:width="700"', result[1])
        self.assertIn('first.png', result[1])
        self.assertEqual(result[2], 'More text')
        self.assertIn('ac:width="700"', result[3])
        self.assertIn('second.jpg', result[3])

    def test_image_with_empty_alt_text_and_width(self):
        """Test image with empty alt text and width setting."""
        md = Markdown()
        processor = ImagePreprocessor(md, max_width="800")

        lines = ['![](confluence-attachment:noalt.png)']
        result = processor.run(lines)

        expected = '<ac:image ac:alt="" ac:width="800"><ri:attachment ri:filename="noalt.png" /></ac:image>'
        self.assertEqual(result[0], expected)


if __name__ == '__main__':
    unittest.main()