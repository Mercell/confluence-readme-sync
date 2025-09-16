"""
An extension for the `python-markdown <https://pypi.org/project/Markdown/>`_ package that formats certain elements for Confluence
pages in a nicer way than pure markdown.
"""

import re
import html
from markdown.postprocessors import Postprocessor
from markdown.preprocessors import Preprocessor
from markdown.extensions import Extension
from markdown import Markdown

class SectionLinkPreprocessor(Preprocessor):
    """
    A preprocessor that removes extra hashtags before section links.
    """
    def run(self, lines: list[str]) -> list[str]:
        """
        Removes extra hashtags before section links such that they have only one hashtag.
        """
        modified_lines: list[str] = []
        for line in lines:
            # replace links to sections on the page with one hashtag instead of multiple to work in confluence urls
            modified_lines.append(re.sub(r'\]\(#+', r'](#', line, flags=re.DOTALL))
        return modified_lines

class ImagePreprocessor(Preprocessor):
    """
    A preprocessor that converts confluence-attachment placeholders to Confluence image macros.
    """
    def __init__(self, md, max_width=None):
        """
        Initialize the preprocessor with optional max_width parameter.

        :param md: Markdown instance
        :param max_width: Maximum width for images in pixels (string or None)
        """
        super().__init__(md)
        self.max_width = max_width

    def run(self, lines: list[str]) -> list[str]:
        """
        Converts image references with confluence-attachment: prefix to Confluence image macros.
        """
        modified_lines: list[str] = []
        for line in lines:
            # Replace confluence-attachment: image references with Confluence image macro
            # Pattern: ![alt](confluence-attachment:filename)
            if self.max_width and self.max_width != '0' and self.max_width != '':
                # Include width attribute if max_width is specified
                line = re.sub(
                    r'!\[([^\]]*)\]\(confluence-attachment:([^\)]+)\)',
                    f'<ac:image ac:alt="\\1" ac:width="{self.max_width}"><ri:attachment ri:filename="\\2" /></ac:image>',
                    line
                )
            else:
                # No width restriction, use original size
                line = re.sub(
                    r'!\[([^\]]*)\]\(confluence-attachment:([^\)]+)\)',
                    r'<ac:image ac:alt="\1"><ri:attachment ri:filename="\2" /></ac:image>',
                    line
                )
            modified_lines.append(line)
        return modified_lines


class CodeBlockPostprocessor(Postprocessor):
    """
    A postprocessor that reformats HTML code blocks to Confluence code snippet macros.
    """
    def run(self, text: str) -> str:
        """
        Replaces HTML code blocks with Confluence code snippet macros with language support.
        """
        def decode_and_wrap(match):
            """Helper function to decode HTML entities and wrap in CDATA"""
            language = match.group(1) if match.lastindex >= 1 else "none"
            code_content = match.group(2) if match.lastindex >= 2 else match.group(1)
            # Decode HTML entities in the code content
            decoded_content = html.unescape(code_content)
            return f'<ac:structured-macro ac:name="code"><ac:parameter ac:name="language">{language}</ac:parameter><ac:plain-text-body><![CDATA[{decoded_content}]]></ac:plain-text-body></ac:structured-macro>'

        # First, handle code blocks with language specification
        processed_text = re.sub(
            r'<pre><code class="language-(\w+)">(.*?)</code></pre>',
            decode_and_wrap,
            text,
            flags=re.DOTALL
        )

        # Then handle code blocks without language specification
        processed_text = re.sub(
            r'<pre><code>(.*?)</code></pre>',
            decode_and_wrap,
            processed_text,
            flags=re.DOTALL
        )

        # Map certain languages to supported confluence languages
        if processed_text != text:
            processed_text = re.sub(
                r'<ac:parameter ac:name="language">bash</ac:parameter>',
                r'<ac:parameter ac:name="language">shell</ac:parameter>',
                processed_text,
                flags=re.DOTALL
            )
        return processed_text

class ConfluenceExtension(Extension):
    """
    The extension to be included in the `extensions` argument of the :ref:`Markdown.markdown` function.
    """
    def __init__(self, **kwargs):
        """
        Initialize the extension with optional configuration.

        :param max_image_width: Maximum width for images in pixels (string or None)
        """
        self.config = {
            'max_image_width': [None, 'Maximum width for images in pixels']
        }
        super().__init__(**kwargs)

    def extendMarkdown(self, md: Markdown):
        """
        Adds the processors to the extension.
        """
        md.registerExtension(self)
        max_width = self.getConfig('max_image_width')
        md.preprocessors.register(ImagePreprocessor(md, max_width=max_width), 'confluence_images', 0)
        md.preprocessors.register(SectionLinkPreprocessor(md), 'confluence_section_links', 1)
        md.postprocessors.register(CodeBlockPostprocessor(md), 'confluence_code_block', 0)

def makeExtension(*args, **kwargs):
    """
    Initializes the Confluence extension.
    """
    return ConfluenceExtension(*args, **kwargs)
