"""
Image processing utilities for handling local images in markdown files.
"""

import re
import os
import logging
from typing import List, Tuple, Dict
from pathlib import Path


class ImageProcessor:
    """
    Processes markdown content to find and handle image references.
    """

    def __init__(self, base_path: str = None):
        """
        Initialize the image processor.

        :param base_path: Base path for resolving relative image paths
        """
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.uploaded_attachments: Dict[str, str] = {}

    def extract_images(self, markdown_content: str) -> List[Tuple[str, str, str]]:
        """
        Extract all image references from markdown content.

        :param markdown_content: The markdown content to process
        :return: List of tuples (full_match, alt_text, image_path)
        """
        # Pattern to match markdown images: ![alt text](path)
        pattern = r'!\[([^\]]*)\]\(([^\)]+)\)'
        matches = re.findall(pattern, markdown_content)

        result = []
        for match in matches:
            alt_text, image_path = match
            full_match = f'![{alt_text}]({image_path})'
            result.append((full_match, alt_text, image_path))

        return result

    def is_local_path(self, path: str) -> bool:
        """
        Check if a path is local (not a URL).

        :param path: The path to check
        :return: True if local path, False if URL
        """
        # Check if path starts with http://, https://, or ftp://
        url_patterns = ['http://', 'https://', 'ftp://']
        return not any(path.startswith(pattern) for pattern in url_patterns)

    def resolve_image_path(self, relative_path: str) -> Path:
        """
        Resolve a relative image path to an absolute path.

        :param relative_path: The relative path from markdown
        :return: Absolute path to the image file
        """
        if os.path.isabs(relative_path):
            return Path(relative_path)

        # Try to resolve relative to base path
        resolved = self.base_path / relative_path
        return resolved

    def get_filename_from_path(self, path: str) -> str:
        """
        Extract filename from a path.

        :param path: The file path
        :return: The filename
        """
        return os.path.basename(path)

    def process_markdown_images(self, markdown_content: str) -> Tuple[str, List[Dict]]:
        """
        Process markdown content to identify local images that need uploading.

        :param markdown_content: The markdown content to process
        :return: Tuple of (modified_markdown, list of images to upload)
        """
        images = self.extract_images(markdown_content)
        images_to_upload = []
        modified_content = markdown_content

        for full_match, alt_text, image_path in images:
            if self.is_local_path(image_path):
                resolved_path = self.resolve_image_path(image_path)
                logging.debug(f"Resolving image path: {image_path} -> {resolved_path} (base_path: {self.base_path})")

                if resolved_path.exists():
                    filename = self.get_filename_from_path(image_path)

                    # Add to upload list if not already uploaded
                    if str(resolved_path) not in self.uploaded_attachments:
                        images_to_upload.append({
                            'path': str(resolved_path),
                            'filename': filename,
                            'alt_text': alt_text,
                            'original_ref': full_match
                        })

                    # Replace markdown image with placeholder that will be converted
                    # to Confluence format later
                    placeholder = f'![{alt_text}](confluence-attachment:{filename})'
                    modified_content = modified_content.replace(full_match, placeholder)
                else:
                    # Try multiple fallback locations for the image
                    found = False
                    attempts = [resolved_path]

                    # Try workspace root if GITHUB_WORKSPACE is set
                    if 'GITHUB_WORKSPACE' in os.environ:
                        workspace_root = Path(os.environ['GITHUB_WORKSPACE'])
                        workspace_fallback = workspace_root / image_path
                        attempts.append(workspace_fallback)

                        # Also try combining markdown's subdirectory with image path
                        # e.g., if markdown is in docs/ and image ref is img/pic.png
                        # try docs/img/pic.png from workspace root
                        if self.base_path != workspace_root:
                            try:
                                relative_base = self.base_path.relative_to(workspace_root)
                                combined_path = workspace_root / relative_base / image_path
                                attempts.append(combined_path)
                            except ValueError:
                                # base_path is not relative to workspace_root
                                pass

                    for attempt_path in attempts:
                        if attempt_path.exists():
                            logging.info(f"Found image at: {attempt_path}")
                            filename = self.get_filename_from_path(image_path)

                            if str(attempt_path) not in self.uploaded_attachments:
                                images_to_upload.append({
                                    'path': str(attempt_path),
                                    'filename': filename,
                                    'alt_text': alt_text,
                                    'original_ref': full_match
                                })

                            placeholder = f'![{alt_text}](confluence-attachment:{filename})'
                            modified_content = modified_content.replace(full_match, placeholder)
                            found = True
                            break

                    if not found:
                        logging.warning(f"Image file not found. Tried paths:")
                        for attempt_path in attempts:
                            logging.warning(f"  - {attempt_path}")

        return modified_content, images_to_upload

    def mark_as_uploaded(self, local_path: str, attachment_name: str):
        """
        Mark an image as uploaded to avoid duplicate uploads.

        :param local_path: The local path of the uploaded image
        :param attachment_name: The name of the attachment in Confluence
        """
        self.uploaded_attachments[local_path] = attachment_name