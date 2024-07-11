import os
from typing import Dict
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.io as pio
import plotly.express as px


class Plotter:
    def __init__(self, counts, stats: Dict):
        self.counts = counts
        self.stats = stats
        self.app = dash.Dash(__name__)
        self._setup_layout()
        self._setup_callbacks()

    def save_figure(self, fig, filename):
        output_dir = "saved_graphs"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        pio.write_image(fig, os.path.join(output_dir, filename))

    def _setup_layout(self):
        # Main layout components
        self.app.layout = html.Div(
            [
                html.H3("Select Plot Type"),
                dcc.Dropdown(
                    id="plot-type-dropdown",
                    options=[
                        {"label": "Total Changes by Label", "value": "changes-label"},
                        {
                            "label": "Total Changes by Collection",
                            "value": "changes-collection",
                        },
                        {
                            "label": "Top 5 Most Updated Files by Collection",
                            "value": "top-files",
                        },
                        {"label": "Total Releases by Label", "value": "releases-label"},
                        {
                            "label": "Total Releases by Collection",
                            "value": "releases-collection",
                        },
                        {
                            "label": "Avg. Complexity by Collection",
                            "value": "avg-complexity",
                        },
                        {
                            "label": "Top 5 Most Complex Files by Collection",
                            "value": "top-complex-files",
                        },
                        {
                            "label": "New Modules Over Time by Label",
                            "value": "modules-overtime-label",
                        },
                        {
                            "label": "Changes Over Time by Collection",
                            "value": "changes-overtime-collection",
                        },
                    ],
                    value="changes-label",
                ),
                html.Div(
                    id="graph-container"
                ),  # Container for dynamic graph components
            ]
        )

    def _setup_callbacks(self):
        @self.app.callback(
            Output("graph-container", "children"),
            [Input("plot-type-dropdown", "value")],
        )
        def update_graphs(plot_type: str):
            if plot_type == "changes-label":
                return self._plot_changes_per_label()
            elif plot_type == "changes-collection":
                return self._plot_changes_per_collection()
            if plot_type == "top-files":
                return self._plot_most_updated_files()
            elif plot_type == "releases-label":
                return self._plot_releases_per_label()
            elif plot_type == "releases-collection":
                return self._plot_releases_per_collection()
            elif plot_type == "top-complex-files":
                return self._plot_most_complex_files()
            elif plot_type == "avg-complexity":
                return self._plot_average_complexity()
            elif plot_type == "modules-overtime-label":
                return self._plot_modules_overtime_per_label()
            elif plot_type == "changes-overtime-collection":
                # Create the layout with a graph for each collection
                return html.Div(
                    [
                        html.H1("Changes Over Time by Collection"),
                        *[
                            html.Div(
                                [
                                    dcc.Graph(
                                        id=f"{collection_name}-graph",
                                        figure=self._plot_changes_overtime_per_collection(
                                            collection_name
                                        ),
                                    )
                                ]
                            )
                            for collection_name in self.counts["changes_overtime"][
                                "collection"
                            ].unique()
                        ],
                    ]
                )
            else:
                return html.Div("Select a plot type")

    def _plot_changes_overtime_per_collection(self, collection_name):
        df = self.counts["changes_overtime"]

        # Filter the DataFrame for the specific collection
        collection_df = df[df["collection"] == collection_name]

        # Melt the DataFrame
        melted_df = collection_df.melt(
            id_vars=["version", "release_date", "label", "collection"],
            var_name="change_type",
            value_name="count",
        )

        # Drop rows where count is NaN
        melted_df = melted_df.dropna(subset=["count"])

        # Create the plotly figure
        fig = px.scatter(
            melted_df,
            x="release_date",
            y="count",
            color="change_type",
            title=f"Changes Over Time by {collection_name}",
            labels={
                "release_date": "Release Date",
                "count": "Count",
                "change_type": "Change Type",
            },
            symbol="change_type",
        )

        fig.update_traces(
            marker=dict(size=12, line=dict(width=2, color="DarkSlateGrey")),
            selector=dict(mode="markers"),
        )

        self.save_figure(fig, f"changes_overtime_{collection_name}.png")

        return fig

    def _plot_modules_overtime_per_label(self):
        df = self.counts["changes_overtime"]

        # Melt the DataFrame to long format
        melted_df = df.melt(
            id_vars=["version", "release_date", "label"],
            var_name="change_type",
            value_name="count",
        )

        # Filter to include 'modules' and 'plugins' change types and drop NaN values
        melted_df = melted_df[
            (melted_df["change_type"].isin(["modules", "plugins"]))
            & (~melted_df["count"].isna())
        ]

        # Plot the pie chart
        fig = px.scatter(
            melted_df,
            y="count",
            x="release_date",
            color="label",
            title="New Modules Over Time per Label",
            symbol="label",
        )

        fig.update_layout(xaxis_title="Release Date", yaxis_title="New Module Count")

        # Save the figure locally
        self.save_figure(fig, "module_overtime_label.png")

        # Define the layout of the Dash app
        return html.Div(
            [
                html.H1("New Modules Over Time per Label"),
                dcc.Graph(id="module-count-label", figure=fig),
            ]
        )

    def _plot_changes_per_label(self):
        df = self.counts["changes_overtime"]

        # Melt the DataFrame
        melted_df = df.melt(
            id_vars=["label", "version", "release_date", "collection"],
            var_name="change_type",
            value_name="count",
        )

        # Filter out rows with NaN values in count
        melted_df = melted_df[~melted_df["count"].isna()]

        fig = px.bar(
            melted_df,
            x="change_type",
            y="count",
            color="label",
            title="Changes per Version by Label",
            barmode="group",
            labels={"count": "Change Count", "version": "Release"},
        )

        # Update layout
        fig.update_layout(barmode="group", xaxis={"categoryorder": "total descending"})

        self.save_figure(fig, "changes_label.png")

        # Layout of the Dash app
        return html.Div(
            [
                html.H1("Changes per Version by Label"),
                dcc.Graph(id="changes-label", figure=fig),
            ]
        )

    def _plot_changes_per_collection(self):
        graphs = []

        df = self.counts["changes_overtime"]

        # Melt the DataFrame to long format
        melted_df = df.melt(
            id_vars=["label", "version", "release_date", "collection"],
            var_name="change_type",
            value_name="count",
        )

        # Filter out rows with NaN values in count
        melted_df = melted_df[~melted_df["count"].isna()]

        # Plot for each collection
        for collection in melted_df["collection"].unique():
            df_collection = melted_df[melted_df["collection"] == collection]
            fig = px.bar(
                df_collection,
                x="version",
                y="count",
                color="change_type",
                title=f"Changes Over Time for {collection}",
                barmode="group",
                labels={"count": "Change Count", "version": "Release"},
            )

            fig.update_layout(
                title=f"Changes per Version for Collection: {collection}",
                xaxis_title="Version",
                yaxis_title="Count",
                height=600,
            )

            self.save_figure(fig, f"changes_version_{collection}.png")

            # Append the graph to the graphs list
            graphs.append(dcc.Graph(figure=fig))

        # Layout of the Dash app
        return html.Div(
            children=[
                html.H1("Changes per Version for Collection"),
                html.Div(graphs),  # Display all graphs in a single HTML div
            ]
        )

    def _plot_most_updated_files(self):
        graphs = []
        most_updated = self.counts["most_updated_files"]

        # Iterate over each collection to create a separate graph
        for collection in most_updated["collection"].unique():
            # Filter data for the current collection
            data_collection = most_updated[most_updated["collection"] == collection]

            # Create figure
            fig = px.bar(
                data_collection,
                x="file_name",
                y="count",
                title=f"Top 5 Most Updated Files by Collection: {collection}",
            )

            # Save the figure
            self.save_figure(fig, f"top_files_plot_{collection}.png")

            # Add the figure to the list of graphs
            graphs.append(dcc.Graph(figure=fig))

        # Layout of the Dash app
        return html.Div(
            children=[
                html.H1("Top 5 Most Updated Files by Collection"),
                html.Div(graphs),  # Display all graphs in a single HTML div
            ]
        )

    def _plot_releases_per_label(self):
        df = self.counts["flatten"]

        release_counts = df["label"].value_counts().reset_index()
        release_counts.columns = ["label", "count"]

        # Plot the pie chart
        fig = px.pie(
            release_counts,
            values="count",
            names="label",
            title="Total Releases by Label",
        )

        # Save the figure locally
        self.save_figure(fig, "release_counts_per_label.png")

        # Define the layout of the Dash app
        return html.Div(
            [
                html.H1("Total Releases by Label"),
                dcc.Graph(id="release-counts-label", figure=fig),
            ]
        )

    def _plot_releases_per_collection(self):
        df = self.counts["flatten"]

        df_counts = df["collection"].value_counts().reset_index()
        df_counts.columns = ["collection", "count"]

        # Plot the pie chart
        fig = px.bar(
            df_counts, y="count", x="collection", title="Total Releases by Label"
        )

        # Save the figure locally
        self.save_figure(fig, "release_counts_per_collection.png")

        # Define the layout of the Dash app
        return html.Div(
            [
                html.H1("Total Releases by Label"),
                dcc.Graph(id="release-counts-collection", figure=fig),
            ]
        )

    def _plot_average_complexity(self):
        labels = []
        values = []
        colors = (
            px.colors.qualitative.Alphabet
        )  # Using Plotly's qualitative color scheme
        for label, data in self.stats.items():
            labels.extend(data.keys())
            values.extend([float(value["avg_complexity"]) for value in data.values()])

        # Generate a color for each collection based on its name or index
        collection_colors = {
            collection: colors[i % len(colors)] for i, collection in enumerate(labels)
        }

        fig_data = []

        # Add bars for each plugin
        for i, (collection, count) in enumerate(zip(labels, values)):
            fig_data.append(
                {
                    "x": [collection],
                    "y": [count],
                    "type": "bar",
                    "name": collection,
                    "marker_color": collection_colors[collection],
                    "hoverinfo": "text+y",
                }
            )

        fig_layout = {
            "title": "Avg. Cyclomatic Complexity by Collection",
            "yaxis": {"title": "Avg. Cyclomatic Complexity"},
            "barmode": "group",
            "showlegend": False,
            "margin": {"autoexpand": True},
            "height": 500,
        }

        fig = {
            "data": fig_data,
            "layout": fig_layout,
        }

        # Save the figure
        self.save_figure(fig, "avg_complexity_per_collection.png")

        # Create the Dash layout
        return html.Div(
            [
                html.H1("Avg. Cyclomatic Complexity by Collection"),
                dcc.Graph(id="avg-complexity", figure=fig, style={"width": "100%"}),
            ]
        )

    def _plot_most_complex_files(self):
        plots = []
        colors = (
            px.colors.qualitative.Alphabet
        )
        for _, collections in self.stats.items():
            for collection_name, data in collections.items():
                plugin_colors = {
                    plugin: colors[i % len(colors)]
                    for i, (plugin, _) in enumerate(data["complex_files"][:5])
                }

                fig_data = []

                # Add bars for each plugin
                for i, (plugin, count) in enumerate(data["complex_files"]):
                    fig_data.append(
                        {
                            "x": [i],
                            "y": [count],
                            "type": "bar",
                            "name": plugin,
                            "marker_color": plugin_colors[plugin],
                            "hoverinfo": "text+y",
                        }
                    )

                fig_layout = {
                    "title": f"Top 5 Most Complex Files by Collection {collection_name}",
                    "yaxis": {"title": "Cyclomatic Complexity"},
                    "barmode": "group",
                    "showlegend": True,
                    "legend": {
                        "orientation": "h",
                        "yanchor": "top",
                        "y": -0.3,
                        "xanchor": "center",
                        "x": 0.5,
                    },
                }

                fig = {
                    "data": fig_data,
                    "layout": fig_layout,
                }

                # Save the figure
                self.save_figure(fig, f"most_complex_files_{collection_name}.png")

                plots.append(
                    html.Div(
                        [
                            html.H3(
                                f"Top 5 Most Complex Files by Collection {collection_name}"
                            ),
                            dcc.Graph(
                                id=f"most-complex-files-plot-{collection_name}",
                                figure=fig,
                            ),
                        ]
                    )
                )
        return plots

    def run(self):
        self.app.run_server(debug=True)
