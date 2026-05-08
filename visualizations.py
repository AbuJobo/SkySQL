"""
Visualization module for FAA-style chart rendering.

This module reads flight data from the SQLite database, applies a token-driven
visual design system, and generates publication-style charts with a branded
header, logo area, footer, and consistent layout rules.
"""

from __future__ import annotations

import json
import os
import sqlite3
from copy import deepcopy
from typing import Any

import matplotlib.patches as patches
import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image

DATABASE_PATH = "data/flights_v2.sqlite3"
RESULTS_DIR = "results"
GUIDE_PATH = "visualization_guide.json"

TOKENS = {
    "faa_full_name": "U.S. Federal Aviation Administration",
    "faa_short_name": "U.S. FAA",
    "faa_copyright": "© 2026 U.S. Federal Aviation Administration",
    "source_prefix": "Source",
    "faa_logo_path": "media/FAA_Logo.jpeg",
    "surface_canvas": "#F4F7FB",
    "surface_panel": "#FFFFFF",
    "surface_header": "#E6E9EE",
    "brand_primary": "#5A6B7A",
    "brand_secondary": "#1D4E89",
    "chart_bar_primary": "#2C7FB8",
    "chart_bar_emphasis": "#F6BE00",
    "text_on_dark": "#FFFFFF",
    "text_strong": "#12263A",
    "text_body": "#243B53",
    "text_muted": "#5B6B7A",
    "line_subtle": "#D9E2EC",
    "font_body_xs": 9,
    "font_body_sm": 10,
    "font_body_md": 11,
    "font_title_lg": 18,
    "font_header_md": 18,
    "figure_landscape": [14, 8.5],
    "export_standard": 160,
    "header_standard": 0.12,
    "logo_standard": [0.014, 0.84, 0.15, 0.14],
    "margins_chart_rotated_labels": {
        "left": 0.07,
        "right": 0.985,
        "top": 0.76,
        "bottom": 0.16,
    },
    "title_under_header": {"x": 0.18, "y": 0.835},
    "subtitle_under_title": {"x": 0.18, "y": 0.798},
    "footer_bottom_right": {"x": 0.985, "y": 0.02},
    "label_share_delayed_percent": "Share of delayed flights in percent",
    "grid_off": False,
    "grid_on": True,
    "grid_dashed": "--",
    "line_width_subtle": 0.8,
    "percent_one_decimal": "{:.1f}",
    "tick_rotation_airline": 45,
}

LOGO_FALLBACK_CENTER_X = 0.06
LOGO_FALLBACK_CENTER_Y = 0.90
LOGO_FALLBACK_RADIUS = 0.022
LOGO_FALLBACK_LINEWIDTH = 1.5

BAR_LABEL_OFFSET_FACTOR = 0.035
BAR_LABEL_OFFSET_MIN = 0.6
DELAY_THRESHOLD_MINUTES = 20
UPPER_LIMIT_PADDING_FACTOR = 1.14
EMPTY_CHART_UPPER_LIMIT = 10
BAR_EDGE_LINEWIDTH = 0.8


def resolve_token(value: Any) -> Any:
    """
    Resolve token references inside nested guide values.

    Strings matching token keys are replaced by the token value. Dictionaries
    and lists are resolved recursively.
    """
    if isinstance(value, dict):
        return {key: resolve_token(inner_value) for key, inner_value in value.items()}
    if isinstance(value, list):
        return [resolve_token(inner_value) for inner_value in value]
    if isinstance(value, str) and value in TOKENS:
        return TOKENS[value]
    return value


def deep_update(target: dict, updates: dict) -> dict:
    """
    Recursively merge updates into a target dictionary.
    """
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            deep_update(target[key], value)
        else:
            target[key] = value
    return target


class VisualizationBase:
    """
    Base class for token-driven chart creation.
    """

    def __init__(self, guide_path: str = GUIDE_PATH) -> None:
        self.guide_path = guide_path
        self.guide = self.load_guide(guide_path)

    def load_guide(self, guide_path: str) -> dict:
        """
        Load the visualization guide and merge tuned token overrides.
        """
        with open(guide_path, "r", encoding="utf-8") as guide_file:
            raw = json.load(guide_file)

        tuned_values = raw.get("_tuned_token_values", {})
        resolved = resolve_token(raw)

        if tuned_values:
            deep_update(resolved, resolve_token(tuned_values))

        if "x_tick_rotation" not in resolved:
            resolved["x_tick_rotation"] = TOKENS["tick_rotation_airline"]
        else:
            resolved["x_tick_rotation"] = resolve_token(resolved["x_tick_rotation"])

        return resolved

    def create_figure(self):
        """
        Create a Matplotlib figure and axis using configured guide values.
        """
        figure_size = tuple(self.guide["layout"]["figure_size"])
        fig, ax = plt.subplots(figsize=figure_size)
        fig.patch.set_facecolor(self.guide["palette"]["background"])
        ax.set_facecolor(self.guide["palette"]["panel"])
        return fig, ax

    def load_logo(self):
        """
        Load the configured logo file if it exists.
        """
        logo_path = self.guide["branding"]["logo_path"]
        if logo_path and os.path.exists(logo_path):
            try:
                return Image.open(logo_path)
            except Exception:
                return None
        return None

    def apply_axis_style(self, ax) -> None:
        """
        Apply consistent axis, grid, and spine styling.
        """
        ax.tick_params(
            axis="x",
            labelsize=self.guide["typography"]["tick_label"],
            colors=self.guide["palette"]["body"],
        )
        ax.tick_params(
            axis="y",
            labelsize=self.guide["typography"]["tick_label"],
            colors=self.guide["palette"]["body"],
        )

        if self.guide["chart_defaults"]["grid_y"]:
            ax.yaxis.grid(
                True,
                linestyle=self.guide["chart_defaults"]["grid_line_style"],
                linewidth=self.guide["chart_defaults"]["grid_line_width"],
                color=self.guide["palette"]["grid"],
            )

        if not self.guide["chart_defaults"]["grid_x"]:
            ax.xaxis.grid(False)

        ax.set_axisbelow(True)

        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)

        ax.spines["left"].set_color(self.guide["palette"]["grid"])
        ax.spines["bottom"].set_color(self.guide["palette"]["grid"])

    def draw_logo(self, fig) -> None:
        """
        Draw the configured logo in the header area.

        If the image is unavailable, draw a small fallback marker.
        """
        logo = self.load_logo()
        if logo is not None:
            x, y, width, height = self.guide["layout"]["logo_box"]
            logo_axis = fig.add_axes([x, y, width, height], zorder=4)
            logo_axis.imshow(logo)
            logo_axis.axis("off")
            return

        fallback_circle = patches.Circle(
            (LOGO_FALLBACK_CENTER_X, LOGO_FALLBACK_CENTER_Y),
            LOGO_FALLBACK_RADIUS,
            transform=fig.transFigure,
            facecolor=TOKENS["chart_bar_emphasis"],
            edgecolor="#FFFFFF",
            linewidth=LOGO_FALLBACK_LINEWIDTH,
            zorder=4,
        )
        fig.patches.append(fallback_circle)

    def draw_header(self, fig, title: str, subtitle: str) -> None:
        """
        Draw the branded header, chart title, and subtitle.
        """
        header_height = self.guide["layout"]["header_height"]
        header_rect = patches.Rectangle(
            (0, 1 - header_height),
            1,
            header_height,
            transform=fig.transFigure,
            color=self.guide["palette"]["header"],
            zorder=2,
            clip_on=False,
        )
        fig.patches.append(header_rect)

        self.draw_logo(fig)

        fig.text(
            self.guide["layout"]["title_position"]["x"],
            self.guide["layout"]["title_position"]["y"],
            title,
            fontsize=self.guide["typography"]["title"],
            color=self.guide["palette"]["title"],
            fontweight="bold",
            ha="left",
            va="bottom",
        )
        fig.text(
            self.guide["layout"]["subtitle_position"]["x"],
            self.guide["layout"]["subtitle_position"]["y"],
            subtitle,
            fontsize=self.guide["typography"]["subtitle"],
            color=self.guide["palette"]["subtitle"],
            ha="left",
            va="bottom",
        )

    def draw_footer(self, fig, source_text: str) -> None:
        """
        Draw the source and copyright footer.
        """
        footer_text = (
            f"{self.guide['branding']['source_prefix']}: {source_text}    "
            f"{self.guide['branding']['copyright']}"
        )
        footer_pos = self.guide["layout"]["footer_position"]
        fig.text(
            footer_pos["x"],
            footer_pos["y"],
            footer_text,
            fontsize=self.guide["typography"]["footer"],
            color=self.guide["palette"]["footer"],
            ha="right",
            va="bottom",
        )

    def apply_layout(self) -> None:
        """
        Apply configured margins to the current figure.
        """
        margins = self.guide["layout"]["margins"]
        plt.subplots_adjust(
            left=margins["left"],
            right=margins["right"],
            top=margins["top"],
            bottom=margins["bottom"],
        )

    def save_figure(self, fig, output_file: str) -> None:
        """
        Save the figure to disk and close it afterwards.
        """
        os.makedirs(RESULTS_DIR, exist_ok=True)
        fig.savefig(
            output_file,
            dpi=self.guide["layout"]["dpi"],
            facecolor=fig.get_facecolor(),
            bbox_inches="tight",
        )
        plt.close(fig)
        print(f"Chart saved to {output_file}")


class AirlineDelayBarChart(VisualizationBase):
    """
    Chart for the share of delayed departures per airline.
    """

    def fetch_data(self) -> pd.DataFrame:
        """
        Read airline-level delay shares from the SQLite database.

        Only DEPARTURE_DELAY is used, matching the actual database schema.
        """
        query = f"""
        SELECT
            a.AIRLINE AS airline,
            COUNT(*) AS total_flights,
            SUM(
                CASE
                    WHEN f.DEPARTURE_DELAY IS NOT NULL
                         AND TRIM(CAST(f.DEPARTURE_DELAY AS TEXT)) != ''
                         AND CAST(f.DEPARTURE_DELAY AS INTEGER) >= {DELAY_THRESHOLD_MINUTES}
                    THEN 1
                    ELSE 0
                END
            ) AS delayed_flights
        FROM flights f
        JOIN airlines a
            ON f.AIRLINE = a.ID
        GROUP BY a.AIRLINE
        ORDER BY airline
        """

        connection = sqlite3.connect(DATABASE_PATH)
        try:
            dataframe = pd.read_sql_query(query, connection)
        finally:
            connection.close()

        dataframe["delayed_pct"] = (
            dataframe["delayed_flights"] / dataframe["total_flights"] * 100
        )
        return dataframe.sort_values("delayed_pct", ascending=False)

    def add_bar_labels(self, ax, bars, values) -> None:
        """
        Add labels inside bars using the configured percentage format.
        """
        max_value = max(values) if len(values) else 0
        offset = max(BAR_LABEL_OFFSET_MIN, max_value * BAR_LABEL_OFFSET_FACTOR)

        for bar, value in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() - offset,
                self.guide["chart_defaults"]["bar_label_format"].format(value),
                ha="center",
                va="top",
                color=self.guide["palette"]["bar_text"],
                fontsize=self.guide["typography"]["value_label"],
                fontweight="bold",
            )

    def build_figure(self):
        """
        Build the airline delay bar chart figure.
        """
        dataframe = self.fetch_data()
        fig, ax = self.create_figure()

        bars = ax.bar(
            dataframe["airline"],
            dataframe["delayed_pct"],
            color=self.guide["palette"]["bar_primary"],
            edgecolor=self.guide["palette"]["accent"],
            linewidth=BAR_EDGE_LINEWIDTH,
        )

        self.apply_axis_style(ax)

        ax.set_ylabel(
            self.guide["chart_defaults"]["y_axis_label"],
            fontsize=self.guide["typography"]["axis_label"],
            color=self.guide["palette"]["body"],
        )
        ax.set_xlabel("")

        upper_limit = (
            max(dataframe["delayed_pct"]) * UPPER_LIMIT_PADDING_FACTOR
            if len(dataframe)
            else EMPTY_CHART_UPPER_LIMIT
        )
        ax.set_ylim(0, upper_limit)

        rotation = self.guide.get("x_tick_rotation", TOKENS["tick_rotation_airline"])
        horizontal_alignment = "center" if rotation <= 15 else "right"
        plt.setp(ax.get_xticklabels(), rotation=rotation, ha=horizontal_alignment)

        self.add_bar_labels(ax, bars, dataframe["delayed_pct"])

        self.draw_header(
            fig,
            title="Share of delayed flights by airline",
            subtitle="Delayed flight threshold: departure delay of 20 minutes or more",
        )
        self.draw_footer(fig, "FAA internal flights_v2.sqlite3 dataset")
        self.apply_layout()
        return fig

    def render(self, output_file: str = os.path.join(RESULTS_DIR, "delayed_percentage_by_airline.png")) -> None:
        """
        Render and save the airline delay chart.
        """
        fig = self.build_figure()
        self.save_figure(fig, output_file)


class HourlyDelayBarChart(VisualizationBase):
    """
    Placeholder for a future hourly delay chart.
    """

    def render(self, output_file: str = os.path.join(RESULTS_DIR, "delayed_percentage_by_hour.png")) -> None:
        raise NotImplementedError("HourlyDelayBarChart will be added in a future step.")


class RouteDelayHeatmap(VisualizationBase):
    """
    Placeholder for a future route delay heatmap.
    """

    def render(self, output_file: str = os.path.join(RESULTS_DIR, "route_delay_heatmap.png")) -> None:
        raise NotImplementedError("RouteDelayHeatmap will be added in a future step.")


class RouteDelayMap(VisualizationBase):
    """
    Placeholder for a future route delay map.
    """

    def render(self, output_file: str = os.path.join(RESULTS_DIR, "route_delay_map.png")) -> None:
        raise NotImplementedError("RouteDelayMap will be added in a future step.")


def plot_delayed_percentage_by_airline() -> None:
    """
    Convenience entry point for rendering the airline delay chart.
    """
    AirlineDelayBarChart().render()