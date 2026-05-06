import asyncio
import logging
import os
from pathlib import Path

import dotenv

dotenv.load_dotenv()

from tasks.code_grader import CodeGrader

LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_FILE = LOG_DIR / "code_grader.log"

LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
	level=logging.INFO,
	format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
	handlers=[logging.FileHandler(LOG_FILE)],
)

logger = logging.getLogger(__name__)


async def run_test():
	provider = os.getenv("CODE_GRADER_PROVIDER")
	if not provider:
		provider = os.getenv("JD_MATCH_PROVIDER")

	grader = CodeGrader(provider=provider)

	question = {
		"title": "Two Sum",
		"prompt": (
			"Given an array of integers nums and an integer target, return the indices "
			"of the two numbers such that they add up to target."
		),
		"examples": [
			{
				"input": "nums = [2,7,11,15], target = 9",
				"output": "[0,1]",
			},
		],
		"sample_cases": [
			{
				"input": "nums = [3,2,4], target = 6",
				"output": "[1,2]",
			},
		],
	}

	answer = """
	Use a hashmap to store value->index. For each number x at i, check if target-x exists.
	If yes return [index_of_target_minus_x, i]. Otherwise store x.
	This is O(n) time and O(n) space.
	""".strip()

	logger.info("Grading")
	result = await grader.grade_solution(question=question, answer=answer)
	logger.info("%s", result)


if __name__ == "__main__":
	asyncio.run(run_test())
