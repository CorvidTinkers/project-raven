import asyncio
import logging
import os
from pathlib import Path

import dotenv

dotenv.load_dotenv()

from tasks.q_generator import QuestionGenerator

LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_FILE = LOG_DIR / "q_generator.log"

LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
	level=logging.INFO,
	format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
	handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


async def run_test():
	provider = os.getenv("Q_GENERATOR_PROVIDER")
	if not provider:
		provider = os.getenv("JD_MATCH_PROVIDER")

	generator = QuestionGenerator(provider=provider)

	skills = ["Python", "FastAPI", "PostgreSQL", "Docker"]

	logger.info("Technical questions")
	tech = await generator.generate_technical_questions(skills=skills, n=5)
	for item in tech:
		logger.info("%s", item)

	logger.info("DSA question")
	dsa = await generator.generate_dsa_question(skills=skills, topic="arrays")
	logger.info("%s", dsa)

	logger.info("SQL question")
	sql = await generator.generate_sql_question(skills=skills, topic="joins")
	logger.info("%s", sql)


if __name__ == "__main__":
	asyncio.run(run_test())
