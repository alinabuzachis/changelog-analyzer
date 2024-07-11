import re
from typing import Dict
import pandas as pd


def order_dict(d: Dict) -> Dict:
    return {key: d[key] for key in sorted(d.keys())}


class InsightsGenerator:
    def __init__(self, data: Dict, limit):
        self.data = self._cleanup_changelog_data(data)
        self.limit = limit
        self.counts = {
            "changes_overtime": self._extract_changes_overtime(),
            "most_updated_files": self._extract_most_updated_files(),
            "flatten": self._extract_total_releases(),
        }

    def _extract_total_releases(self):
        # Flatten the data into a list of dictionaries
        release_data = []
        for label, collections in self.data.items():
            for collection, releases in collections.items():
                for version, details in releases.items():
                    release_data.append(
                        {
                            "label": label,
                            "collection": collection,
                            "version": version,
                            "details": details,
                        }
                    )
        # Convert the flattened data into a DataFrame
        df = pd.DataFrame(release_data)

        return df

    def get_x_items_from_dict(self, d: Dict) -> Dict:
        # Convert dictionary items to a list and slice the last x items
        last_x_items = list(d.items())[-self.limit :]
        # Convert the sliced list back to a dictionary
        return dict(last_x_items)

    def _extract_most_updated_files(self) -> Dict:
        # Regex pattern for matching individual entries
        entry_pattern = re.compile(r"^([^\s]+)\s+-\s+(.+)")

        # Function to extract and split terms from a string
        def extract_and_split_terms(s):
            match = re.match(entry_pattern, s)
            if match:
                extracted_string = match.group(1)
                return cleanup_terms(
                    [term.strip() for term in extracted_string.split(",")]
                )

            return []

        # Function to extract and split terms from a string
        def cleanup_terms(terms):
            result = []
            for elem in terms:
                match = elem.split(".")
                if match:
                    # Remove all non-alphanumeric characters (keep only letters and digits)
                    result.append(re.sub(r"\W+", "", match[-1]).lower())
                else:
                    # Remove all non-alphanumeric characters (keep only letters and digits)
                    result.append(re.sub(r"\W+", "", elem).lower())
            return [term for term in result if term]  # Filter out empty terms

        release_data = []

        # Flatten the data into a list of dictionaries
        for label, collections in self.data.items():
            for collection, versions in collections.items():
                if self.limit:
                    sorted_dict = order_dict(versions)
                    versions = self.get_x_items_from_dict(sorted_dict)
                for version, info in versions.items():
                    for key, value in info.items():
                        if key not in ("modules", "plugins"):
                            if isinstance(value, list):
                                for v in value:
                                    result = extract_and_split_terms(v)
                                    if result:
                                        for file_name in result:
                                            release_data.append(
                                                {
                                                    "label": label,
                                                    "collection": collection,
                                                    "file_name": file_name,
                                                }
                                            )

        # Create DataFrame from the flattened data
        df = pd.DataFrame(release_data)

        # Group by label, collection, and file_name and count occurrences
        grouped = (
            df.groupby(["label", "collection", "file_name"])
            .size()
            .reset_index(name="count")
        )

        # Sort and extract top 5 files per collection
        top_files = (
            grouped.groupby(["label", "collection"])
            .apply(lambda x: x.nlargest(5, "count"))
            .reset_index(drop=True)
        )

        return top_files

    def _extract_changes_overtime(self):
        # Initialize a dictionary
        records = []

        for label, collections in self.data.items():
            for collection, versions in collections.items():
                if self.limit:
                    sorted_dict = order_dict(versions)
                    versions = self.get_x_items_from_dict(sorted_dict)
                for version, details in versions.items():
                    record = {
                        "label": label,
                        "version": version,
                        "release_date": details.get("release_date"),
                        "collection": collection,
                    }
                    for change_type in details.keys():
                        if (
                            change_type not in ["release_date", "release_summary"]
                            and details.get(change_type) is not None
                        ):
                            record[change_type] = len(details.get(change_type, []))
                    records.append(record)

        # Convert records to DataFrame
        df = pd.DataFrame(records)

        # Convert release_date to datetime
        df["release_date"] = pd.to_datetime(df["release_date"])

        return df

    def _cleanup_changelog_data(self, data: Dict) -> Dict:
        counts: Dict = {}

        # Aggregate counts per label
        for label, collections in data.items():
            if not counts.get(label):
                counts[label] = {}
            for collection, releases in collections.items():
                counts[label][collection] = {}
                for release, changes in releases.items():
                    changes_dict = {}
                    for category, entries in changes.items():
                        if category == "plugins":
                            changes_dict["plugins"] = []
                            for type, p_info in entries.items():
                                for item in p_info:
                                    changes_dict["plugins"].append(item["name"])
                        elif category == "modules":
                            changes_dict["modules"] = []
                            for module in entries:
                                changes_dict["modules"].append(module["name"])
                        elif category == "changes":
                            for type, info in entries.items():
                                changes_dict[type] = info
                        elif category == "release_date":
                            changes_dict[category] = entries
                    counts[label][collection][release] = changes_dict

        return counts
