# changelog-analyzer: Ansible Changelog Analysis Tool

This repository contains a Python-based tool for analyzing Ansible Collections that use the [``antsibull-changelog``](https://github.com/ansible-community/antsibull-changelog) tool for the release process. This tool parses changelog files (changelog.yml or changelog.yaml), extracts key insights, and generates graphical reports using ``plotly`` and ``dash``.

The tool generates the following insights:

    1. Total Changes by Label
    2. Total Changes by Collection
    3. Top 5 Most Updated Files by Collection
    4. New Modules Over Time by Label
    5. Changes Over Time by Collection
    6. Total Releases by Label
    7. Total Releases by Collection
    8. Avg. Complexity by Collection
    9. Top 5 Most Complex Files by Collection

To generate the insights, the tool follows this process:
- Load the configuration file containing the list of collections to be analyzed.
- Clone each collection locally in a temporary folder.
- Use the latest tag of the collection to check out and load the ``changelogs/changelog.(yml|yaml)`` file.
- Extract the specific insights from points 1 - 7.
    - For metric number 3, the tool relies on the structure of the changelog fragments. Typically, fragments follow this structure:
        ```
        ---
        minor_changes:
            - impacted_component - Descriprion of the change.
        ```

    - The tool identifies the impacted file component by extracting the plugin name, such as ``impacted_component``. If a changelog entry does not follow this structure, it is discarded.

- For each collection, after checking out the latest tag, the ``radon`` library is used to compute the cyclomatic complexity. Additionally, certain folders such as tests/ and plugins/doc_fragments have been ignored during the analysis.
- Plot the insights.


## How to use

### Dependencies

Ensure you have the necessary dependencies installed. You can install them using:

``pip install -r requirements.txt``

### Configuration File

To use this tool, you need to provide a path to a YAML configuration file that lists the collections to be analyzed. The structure of this file should include the following:

- ``limit``: Limits the number of releases per collection to be considered for metrics extraction (e..g., ``limit: 5`` means the latest 5 releases). Limit is applied when insights 1 - 5 are generated.

- ``collections``: A list of collections, where each collection entry may include:
    - ``name``: The name of the collection.
    - ``github_repo``: The link to the GitHub repository of the collection.
    - ``label (optional)``: If not specified, the collection is automatically assigned the label "other".
    - ``min_tag``: Specifies to fetch tags greater than or equal to the provided value for metrics extraction. If ``min_tag`` is specified together with ``limit``, the ``min_tag`` setting will be ignored.

### Running the Application

To run the application, execute the following command:

``python src/main.py collections.yml``

### Accessing the Dash Application

After running the application, the Dash server will start, and you can access the graphical reports via a web browser. By default, the Dash application will be available at ``http://127.0.0.1:8050/``. This will display the dashboard with all the generated insights and graphical reports.

When a type of insight is chosen from the drop-down menu in Dash, the figures will be saved in the ``saved_graphs`` folder.