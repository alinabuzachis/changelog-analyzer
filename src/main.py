import os
import git
import argparse
import logging
import shutil
import subprocess
import tempfile
from collections import defaultdict
from typing import Dict, List
from packaging.version import parse as parse_version
import yaml

from insights import InsightsGenerator
from stats import CodeQualityAnalyzer
from plotter import Plotter


class ChangelogParser:
    def __init__(self, collection_file: str):
        self.collection_file = collection_file
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG)

    def load_collections_from_yaml(self) -> List:
        with open(self.collection_file, "r") as file:
            collections = yaml.safe_load(file)
        return collections

    def load_changelog(self, collection: Dict, limit=None) -> Dict:
        changelog = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        temp_dir = tempfile.mkdtemp(prefix=f'{collection["name"]}_repo_')

        try:
            repo_path = os.path.join(temp_dir, collection["name"])

            # Clone repository if it doesn't exist
            if not os.path.exists(repo_path):
                subprocess.run(["git", "clone", collection["github_repo"], repo_path])

            repo = git.Repo(repo_path)
            tags = repo.git.tag(sort="creatordate").split("\n")

            if len(tags) == 1 and tags[0] == "":
                self.logger.info(
                    f'Collection {collection["name"]} does not have GitHub tags'
                )
                return changelog

            if limit:
                tags = tags[-limit:]

            elif collection.get("min_tag"):
                tags = [
                    tag
                    for tag in tags
                    if parse_version(tag) >= parse_version(collection["min_tag"])
                ]

            # Checkout to the specific tag
            subprocess.run(["git", "checkout", tags[-1]], cwd=repo_path)

            # Check for the existence of changelog files
            changelog_dir = os.path.join(repo_path, "changelogs")
            changelog_files = ["changelog.yml", "changelog.yaml"]
            changelog_found = False

            for changelog_file in changelog_files:
                changelog_path = os.path.join(changelog_dir, changelog_file)
                if os.path.exists(changelog_path):
                    with open(changelog_path, "r") as file:
                        changelog_content = yaml.safe_load(file)
                        changelog[collection["name"]] = changelog_content["releases"]
                    changelog_found = True
                    break  # Stop searching if we've found and loaded the changelog

            if not changelog_found:
                self.logger.info(f"No changelog file found for {collection['name']}")
        except subprocess.CalledProcessError as e:
            self.logger.error(
                f"An error occurred while processing {collection['name']} at tag {tags[-1]}: {e}"
            )
        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {e}")
        finally:
            if temp_dir:
                shutil.rmtree(temp_dir)  # Delete temporary directory

        return changelog

    def _generate_code_quality_stats(self, collection: Dict, limit=None) -> Dict:
        # Initialize CodeQualityAnalyzer for current collection

        def is_empty_dict_or_list(value):
            # Check if the value is an empty dictionary or list, or if it is zero
            if isinstance(value, dict) or isinstance(value, list):
                return not bool(value)
            return False

        def contains_only_empty_values(d):
            # Check that all values in the dictionary are either empty dictionaries/lists or zero values
            return all(is_empty_dict_or_list(v) or v == 0 for v in d.values())

        analyzer = CodeQualityAnalyzer(collection, limit)
        result = analyzer.analyze_collections()
        return (
            {collection["name"]: result}
            if not contains_only_empty_values(result)
            else {}
        )

    def parse(self):
        collections = self.load_collections_from_yaml()
        changelog_data = {}
        stats = {}
        limit = None

        if collections.get("limit"):
            limit = collections["limit"]

        for collection in collections["collections"]:
            self.logger.info(f"Collection: {collection['name']}")
            label = collection.get("label", "other")
            if not changelog_data.get(label):
                changelog_data[label] = {}
            if not stats.get(label):
                stats[label] = {}

            # Fetch the changelog from the GitHub repository based on tags and min_tag
            result = self.load_changelog(collection, limit)
            if not result:
                self.logger.info(
                    f"No changelog available for collection: {collection['name']}. Skipping..."
                )
                continue

            changelog_data[label].update(result)
            result_stats = self._generate_code_quality_stats(collection, limit)
            if result_stats:
                stats[label].update(result_stats)

        if changelog_data:
            self.logger.info("Initialize and run InsightsGenerator")
            data_extractor = InsightsGenerator(changelog_data, limit)
            self.plot(data_extractor.counts, stats)
        else:
            self.logger.warning("No changelog data found for any collections.")

    def plot(self, counts, stats):
        # Create and run the plotter
        self.logger.info("Initialize and run Plotter")
        plotter = Plotter(counts, stats)
        plotter.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse chnagelog.yml files")
    parser.add_argument(
        "collections",
        type=str,
        help="The config file containing the list of collections.",
    )
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    changelog_parser = ChangelogParser(args.collections)
    changelog_parser.parse()
