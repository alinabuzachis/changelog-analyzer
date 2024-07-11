import json
import logging
import os
import git
import shutil
import subprocess
import tempfile
from typing import Dict, Union


def get_top_complex_files(complexity_data, num_files=5):
    file_complexities = []

    # Calculate total complexity for each file
    for file, metrics in complexity_data.items():
        total_complexity = sum(item["complexity"] for item in metrics)
        file_complexities.append((file, total_complexity))

    # Sort files by complexity (descending) and get top num_files
    sorted_files = sorted(file_complexities, key=lambda x: x[1], reverse=True)[
        :num_files
    ]

    return sorted_files


class CodeQualityAnalyzer:
    def __init__(self, collection: Dict, limit=None):
        self.collection = collection
        self.limit = limit
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG)

    def analyze_collections(self) -> Dict:
        temp_dir = None
        results: Dict = {}

        try:
            temp_dir = tempfile.mkdtemp(prefix=f'{self.collection["name"]}_repo_')
            repo_path = os.path.join(temp_dir, self.collection["name"])

            # Clone repository if it doesn't exist
            if not os.path.exists(repo_path):
                subprocess.run(
                    ["git", "clone", self.collection["github_repo"], repo_path]
                )

            repo = git.Repo(repo_path)
            tags = repo.git.tag(sort="creatordate").split("\n")

            # Get the latest tag
            tag = tags[-1]
            # Checkout to the specific tag
            subprocess.run(["git", "checkout", tag], cwd=repo_path)

            # Run code coverage analysis
            # coverage = self.run_coverage_analysis(repo_path)

            # Run code complexity analysis
            avg_complexity, top_complex_files = self.run_complexity_analysis(repo_path)

            # Run code maintainability index analysis
            # maintainability_index = self.run_maintainability_index(repo_path)

            # Combine results
            results = {
                # "coverage": coverage,
                "avg_complexity": avg_complexity,
                "complex_files": top_complex_files,
                # "maintainability_index": maintainability_index,
            }

            return results

        except subprocess.CalledProcessError as e:
            self.logger.error(
                f"An error occurred while processing {self.collection['name']} at tag {tag}: {e}"
            )
        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {e}")
        finally:
            if temp_dir:
                shutil.rmtree(temp_dir)  # Delete temporary directory

    def run_coverage_analysis(self, repo_path) -> Union[int, float]:
        try:
            # Run pytest with coverage and generate JSON report
            subprocess.run(
                ["pytest", "--cov=.", "--cov-report=json"], cwd=repo_path, check=True
            )

            # Read the JSON output
            with open(os.path.join(repo_path, "coverage.json")) as f:
                coverage_data = json.load(f)

            return coverage_data["totals"]["percent_covered"]
        except subprocess.CalledProcessError as e:
            self.logger.error(f"An error occurred during coverage analysis: {e}")
            return 0

    def run_maintainability_index(self, repo_path):
        try:
            # Run radon to collect maintainability index metrics
            mi_result = subprocess.run(
                ["radon", "mi", "-s", "-j", "."],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )

            # Parse the JSON output
            mi_data = json.loads(mi_result.stdout)

            # Calculate average maintainability index
            total_mi = 0
            num_modules = 0
            for module_data in mi_data.values():
                total_mi += module_data["mi"]
                num_modules += 1

            average_mi = total_mi / num_modules if num_modules > 0 else 0

            return average_mi
        except subprocess.CalledProcessError as e:
            self.logger.error(f"An error occurred during complexity analysis: {e}")
            return 0

    def run_complexity_analysis(self, repo_path) -> Union[int, float]:
        try:
            # Run radon to collect complexity metrics
            result = subprocess.run(
                [
                    "radon",
                    "cc",
                    "-s",
                    "-j",
                    "-i",
                    "tests",
                    "-i",
                    "plugins/doc_fragments",
                    "--total-average",
                    "-a",
                    ".",
                ],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )

            # Parse the JSON output
            data = json.loads(result.stdout)

            # Calculate average complexity
            total_complexity = 0
            num_functions = 0
            for file_data in data.values():
                for func_data in file_data:
                    total_complexity += func_data["complexity"]
                    num_functions += 1

            avg_complexity = (
                total_complexity / num_functions if num_functions > 0 else 0
            )

            top_complex_files = get_top_complex_files(data)

            return avg_complexity, top_complex_files
        except subprocess.CalledProcessError as e:
            self.logger.error(f"An error occurred during complexity analysis: {e}")
            return 0
