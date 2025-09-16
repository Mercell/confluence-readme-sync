import json
from os import environ
from typing import Dict
from pathlib import Path
from src.utils import extract_domain_and_page_id
from src.api import ConfluenceClient, GetPageCommand, GetPageCommandInput, EditPageCommand, EditPageCommandInput, UploadAttachmentCommand, UploadAttachmentCommandInput
from src.image_processor import ImageProcessor
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
import markdown
from src.confluence_markdown_extension import ConfluenceExtension
import logging
from src.errors import InvalidParameterError, ConfluenceApiError, SubstringNotFoundError

load_dotenv()

def main() -> None:
    # set up logging module to report info logs
    logging.basicConfig(level=logging.INFO)

    logging.info("Starting README sync...")
    # retrieve and verify env variables
    vars: Dict[str, str] = {}
    for key in ["filepath", "url", "username", "token", "insert_start_text", "insert_end_text"]:
        value = environ.get(f"INPUT_{key.upper()}")
        if not value:
            raise InvalidParameterError(f"Error: Missing value for {key}")
        vars[key] = value

    domain, page_id = extract_domain_and_page_id(vars["url"])

    # set up client
    auth = HTTPBasicAuth(vars["username"], vars["token"])
    client = ConfluenceClient(auth)

    # create get page command
    input = GetPageCommandInput(domain, page_id)
    command = GetPageCommand(input)

    logging.info("Getting confluence page content.")
    response = client.send(command)
    json_response_body = json.loads(response.text)

    # process get page results
    page_status: str = json_response_body["status"]
    page_title: str = json_response_body["title"]
    page_body: str = json_response_body["body"]["storage"]["value"]
    page_version_number: int = json_response_body["version"]["number"]
    if not (page_status and page_title and page_body and page_version_number): raise ConfluenceApiError("Values were not correctly received from Confluence page")
    
    # read markdown file
    logging.info("Reading markdown file.")
    md_text: str
    with open(vars["filepath"], 'r') as f:
        md_text = f.read()

    # Process images in markdown
    logging.info("Processing images in markdown.")
    # Get the directory containing the markdown file
    markdown_file_path = Path(vars["filepath"])
    base_path = markdown_file_path.parent
    logging.info(f"Using base path for images: {base_path}")
    logging.info(f"Markdown file path: {markdown_file_path}")

    # Set GITHUB_WORKSPACE if running in GitHub Actions and not already set
    # This helps with image path resolution
    if 'GITHUB_WORKSPACE' not in environ and 'GITHUB_ACTION' in environ:
        # Try to determine workspace from the filepath
        workspace = str(markdown_file_path.parent)
        environ['GITHUB_WORKSPACE'] = workspace
        logging.info(f"Set GITHUB_WORKSPACE to: {workspace}")

    image_processor = ImageProcessor(base_path=base_path)
    processed_md_text, images_to_upload = image_processor.process_markdown_images(md_text)

    # Upload local images as attachments
    for image_info in images_to_upload:
        try:
            logging.info(f"Uploading image: {image_info['filename']}")
            with open(image_info['path'], 'rb') as img_file:
                upload_input = UploadAttachmentCommandInput(
                    domain=domain,
                    page_id=page_id,
                    filename=image_info['filename'],
                    file_content=img_file,
                    comment="Uploaded by confluence-readme-sync"
                )
                upload_command = UploadAttachmentCommand(upload_input)
                upload_response = client.send(upload_command)

                if upload_response.status_code in [200, 201]:
                    logging.info(f"Successfully uploaded: {image_info['filename']}")
                    image_processor.mark_as_uploaded(image_info['path'], image_info['filename'])
                else:
                    logging.warning(f"Failed to upload {image_info['filename']}: {upload_response.status_code}")
        except Exception as e:
            logging.error(f"Error uploading {image_info['filename']}: {str(e)}")

    # convert markdown file to html
    logging.info("Converting markdown file.")
    converted_html = markdown.markdown(processed_md_text, extensions=['tables', 'fenced_code', ConfluenceExtension()])

    # insert markdown between insert_start_text and insert_end_text
    start_substring: str = vars["insert_start_text"]
    end_substring: str = vars["insert_end_text"]
    start_index = page_body.find(start_substring)
    end_index = page_body.find(end_substring)
    if start_index == -1 or end_index == -1 or start_index > end_index: raise SubstringNotFoundError("Insert after string was not found in the body of the Confluence page")
    page_body = page_body[:start_index + len(start_substring)] + converted_html + page_body[end_index:end_index + len(end_substring)] + page_body[end_index + len(end_substring):]

    # create edit page command
    input = EditPageCommandInput(domain, page_id, page_status, page_title, page_body, page_version_number)
    command = EditPageCommand(input)

    logging.info("Updating confluence page.")
    response = client.send(command)
    response.raise_for_status()
    logging.info("Sync successful!")
    return

if __name__ == "__main__":
    main()