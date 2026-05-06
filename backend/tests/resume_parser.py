import asyncio
import logging
import os
from pathlib import Path

from fastapi import UploadFile
import dotenv

dotenv.load_dotenv()

from tasks.resume_parser import ResumeSkillMatcher

LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_FILE = LOG_DIR / "resume_parser.log"

LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.FileHandler(LOG_FILE)],
)

logger = logging.getLogger(__name__)

async def run_test():
    # 1. Path to a real PDF on your machine
    file_path = "/home/gokul/Downloads/resume.pdf"  # Update this to a valid PDF pat
    
    if not os.path.exists(file_path):
        logger.error("File not found at %s", file_path)
        return

    # 2. Open the file and wrap it in UploadFile
    # We use 'rb' (read binary) because PDFs are binary files
    with open(file_path, "rb") as f:
        fake_upload_file = UploadFile(
            filename=os.path.basename(file_path), 
            file=f
        )

        # 3. Define a dummy Job Description
        jd_text = """
    We are looking for a Software Engineer with experience in web development and cloud platforms.
    Requirements:
    - Proficiency in Python and Django
    - Experience with React or similar frontend frameworks
    - Familiarity with AWS or other cloud services
    - Strong problem-solving skills
    """
        logger.info("Starting extraction")
        try:
            matcher = ResumeSkillMatcher()
            results = await matcher.extract_aligned_skills_from_resume_pdf(
                resume_file=fake_upload_file,
                jd_text=jd_text,
            )

            logger.info("Extraction results")
            for skill in results:
                logger.info("%s", skill)

        except Exception as e:
            logger.exception("Extraction failed: %s", e)

if __name__ == "__main__":
    asyncio.run(run_test())
