"""
Interactive Streamlit tuner for visualization layout and branding tokens.

The app previews the active Matplotlib chart, allows token adjustments for
header, logo, margins, and label rotation, and writes tuned values back to the
JSON guide file.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

import visualizations

GUIDE_PATH = Path("visualization_guide.json")

DEFAULT_HEADER_HEIGHT = 0.12
DEFAULT_LOGO_BOX = [0.014, 0.84, 0.15, 0.14]
DEFAULT_MARGINS = {
    "left": 0.07,
    "right": 0.985,
    "top": 0.76,
    "bottom": 0.16,
}
DEFAULT_TITLE_POSITION = {"x": 0.18, "y": 0.835}
DEFAULT_SUBTITLE_POSITION = {"x": 0.18, "y": 0.798}
DEFAULT_FOOTER_POSITION = {"x": 0.985, "y": 0.02}
DEFAULT_TICK_ROTATION = 45

HEADER_MIN = 0.05
HEADER_MAX = 0.22
HEADER_STEP = 0.005

LOGO_X_MIN = 0.0
LOGO_X_MAX = 0.20
LOGO_Y_MIN = 0.72
LOGO_Y_MAX = 0.92
LOGO_W_MIN = 0.04
LOGO_W_MAX = 0.30
LOGO_H_MIN = 0.04
LOGO_H_MAX = 0.24
LOGO_STEP = 0.001

MARGIN_LEFT_MIN = 0.01
MARGIN_LEFT_MAX = 0.20
MARGIN_RIGHT_MIN = 0.80
MARGIN_RIGHT_MAX = 1.00
MARGIN_TOP_MIN = 0.50
MARGIN_TOP_MAX = 0.95
MARGIN_BOTTOM_MIN = 0.05
MARGIN_BOTTOM_MAX = 0.30
MARGIN_STEP = 0.005

TITLE_X_MIN = 0.01
TITLE_X_MAX = 0.40
TITLE_Y_MIN = 0.68
TITLE_Y_MAX = 0.92
SUBTITLE_X_MIN = 0.01
SUBTITLE_X_MAX = 0.40
SUBTITLE_Y_MIN = 0.64
SUBTITLE_Y_MAX = 0.90
POSITION_STEP = 0.005

FOOTER_X_MIN = 0.70
FOOTER_X_MAX = 1.00
FOOTER_Y_MIN = 0.00
FOOTER_Y_MAX = 0.10
FOOTER_X_STEP = 0.005
FOOTER_Y_STEP = 0.002

TICK_ROTATION_MIN = 0
TICK_ROTATION_MAX = 90
TICK_ROTATION_STEP = 1

PREVIEW_DPI = 140

st.set_page_config(page_title="FAA Guide Tuner", layout="wide")


@st.cache_data
def load_guide() -> dict:
    """
    Load the JSON visualization guide from disk.
    """
    with GUIDE_PATH.open("r", encoding="utf-8") as guide_file:
        return json.load(guide_file)


def save_guide(guide: dict) -> None:
    """
    Persist the modified visualization guide to disk.
    """
    with GUIDE_PATH.open("w", encoding="utf-8") as guide_file:
        json.dump(guide, guide_file, indent=2)


def get_initial_tuned_values(guide: dict) -> dict:
    """
    Build the initial UI state from defaults and persisted tuned values.
    """
    defaults = {
        "header_standard": DEFAULT_HEADER_HEIGHT,
        "logo_standard": DEFAULT_LOGO_BOX.copy(),
        "margins_chart_rotated_labels": DEFAULT_MARGINS.copy(),
        "title_under_header": DEFAULT_TITLE_POSITION.copy(),
        "subtitle_under_title": DEFAULT_SUBTITLE_POSITION.copy(),
        "footer_bottom_right": DEFAULT_FOOTER_POSITION.copy(),
        "tick_rotation_airline": DEFAULT_TICK_ROTATION,
    }

    saved = guide.get("_tuned_token_values", {})
    for key, value in saved.items():
        defaults[key] = value

    if "x_tick_rotation" in guide and isinstance(guide["x_tick_rotation"], (int, float)):
        defaults["tick_rotation_airline"] = guide["x_tick_rotation"]

    return defaults


def deep_update(target: dict, updates: dict) -> dict:
    """
    Recursively merge updates into a nested dictionary.
    """
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            deep_update(target[key], value)
        else:
            target[key] = value
    return target


def collect_tuned_values(ui: dict) -> dict:
    """
    Convert UI widget values into the token structure used by the guide.
    """
    return {
        "header_standard": ui["header_standard"],
        "logo_standard": [ui["logo_x"], ui["logo_y"], ui["logo_w"], ui["logo_h"]],
        "margins_chart_rotated_labels": {
            "left": ui["margin_left"],
            "right": ui["margin_right"],
            "top": ui["margin_top"],
            "bottom": ui["margin_bottom"],
        },
        "title_under_header": {"x": ui["title_x"], "y": ui["title_y"]},
        "subtitle_under_title": {"x": ui["subtitle_x"], "y": ui["subtitle_y"]},
        "footer_bottom_right": {"x": ui["footer_x"], "y": ui["footer_y"]},
        "tick_rotation_airline": ui["tick_rotation_airline"],
    }


def serialize_token_value(value: Any) -> str:
    """
    Convert nested token values into Arrow-safe string representations.
    """
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def tuned_values_to_table(tuned: dict) -> pd.DataFrame:
    """
    Build a display table for the currently active tuned values.

    Complex values are serialized to strings to avoid Arrow conversion warnings.
    """
    rows = [
        {"token": "header_standard", "value": serialize_token_value(tuned["header_standard"])},
        {"token": "logo_standard", "value": serialize_token_value(tuned["logo_standard"])},
        {
            "token": "margins_chart_rotated_labels",
            "value": serialize_token_value(tuned["margins_chart_rotated_labels"]),
        },
        {"token": "title_under_header", "value": serialize_token_value(tuned["title_under_header"])},
        {"token": "subtitle_under_title", "value": serialize_token_value(tuned["subtitle_under_title"])},
        {"token": "footer_bottom_right", "value": serialize_token_value(tuned["footer_bottom_right"])},
        {"token": "tick_rotation_airline", "value": serialize_token_value(tuned["tick_rotation_airline"])},
    ]
    return pd.DataFrame(rows)


def render_active_chart(tuned: dict):
    """
    Render the current chart preview with temporary tuned values.
    """
    chart = visualizations.AirlineDelayBarChart()
    deep_update(chart.guide, visualizations.resolve_token(tuned))
    chart.guide["x_tick_rotation"] = tuned["tick_rotation_airline"]
    return chart.build_figure()


def fig_to_png_bytes(fig) -> bytes:
    """
    Convert a Matplotlib figure into PNG bytes for Streamlit preview/download.
    """
    buffer = io.BytesIO()
    fig.savefig(
        buffer,
        format="png",
        dpi=PREVIEW_DPI,
        facecolor=fig.get_facecolor(),
        bbox_inches="tight",
    )
    buffer.seek(0)
    return buffer.getvalue()


def main() -> None:
    """
    Run the Streamlit tuner interface.
    """
    st.title("FAA Visualization Guide Tuner")
    st.caption("Interactive tuning for the active FAA chart layout and branding tokens.")

    guide = load_guide()
    initial = get_initial_tuned_values(guide)

    with st.sidebar:
        st.subheader("Layout controls")
        ui = {}

        ui["header_standard"] = st.slider(
            "Header height",
            HEADER_MIN,
            HEADER_MAX,
            float(initial["header_standard"]),
            HEADER_STEP,
        )

        st.markdown("### Logo box")
        ui["logo_x"] = st.slider("Logo x", LOGO_X_MIN, LOGO_X_MAX, float(initial["logo_standard"][0]), LOGO_STEP)
        ui["logo_y"] = st.slider("Logo y", LOGO_Y_MIN, LOGO_Y_MAX, float(initial["logo_standard"][1]), LOGO_STEP)
        ui["logo_w"] = st.slider("Logo width", LOGO_W_MIN, LOGO_W_MAX, float(initial["logo_standard"][2]), LOGO_STEP)
        ui["logo_h"] = st.slider("Logo height", LOGO_H_MIN, LOGO_H_MAX, float(initial["logo_standard"][3]), LOGO_STEP)

        st.markdown("### Margins")
        ui["margin_left"] = st.slider(
            "Left",
            MARGIN_LEFT_MIN,
            MARGIN_LEFT_MAX,
            float(initial["margins_chart_rotated_labels"]["left"]),
            MARGIN_STEP,
        )
        ui["margin_right"] = st.slider(
            "Right",
            MARGIN_RIGHT_MIN,
            MARGIN_RIGHT_MAX,
            float(initial["margins_chart_rotated_labels"]["right"]),
            MARGIN_STEP,
        )
        ui["margin_top"] = st.slider(
            "Top",
            MARGIN_TOP_MIN,
            MARGIN_TOP_MAX,
            float(initial["margins_chart_rotated_labels"]["top"]),
            MARGIN_STEP,
        )
        ui["margin_bottom"] = st.slider(
            "Bottom",
            MARGIN_BOTTOM_MIN,
            MARGIN_BOTTOM_MAX,
            float(initial["margins_chart_rotated_labels"]["bottom"]),
            MARGIN_STEP,
        )

        st.markdown("### Title and subtitle")
        ui["title_x"] = st.slider("Title x", TITLE_X_MIN, TITLE_X_MAX, float(initial["title_under_header"]["x"]), POSITION_STEP)
        ui["title_y"] = st.slider("Title y", TITLE_Y_MIN, TITLE_Y_MAX, float(initial["title_under_header"]["y"]), POSITION_STEP)
        ui["subtitle_x"] = st.slider(
            "Subtitle x",
            SUBTITLE_X_MIN,
            SUBTITLE_X_MAX,
            float(initial["subtitle_under_title"]["x"]),
            POSITION_STEP,
        )
        ui["subtitle_y"] = st.slider(
            "Subtitle y",
            SUBTITLE_Y_MIN,
            SUBTITLE_Y_MAX,
            float(initial["subtitle_under_title"]["y"]),
            POSITION_STEP,
        )

        st.markdown("### Footer")
        ui["footer_x"] = st.slider(
            "Footer x",
            FOOTER_X_MIN,
            FOOTER_X_MAX,
            float(initial["footer_bottom_right"]["x"]),
            FOOTER_X_STEP,
        )
        ui["footer_y"] = st.slider(
            "Footer y",
            FOOTER_Y_MIN,
            FOOTER_Y_MAX,
            float(initial["footer_bottom_right"]["y"]),
            FOOTER_Y_STEP,
        )

        st.markdown("### Axis labels")
        ui["tick_rotation_airline"] = st.slider(
            "X tick rotation",
            TICK_ROTATION_MIN,
            TICK_ROTATION_MAX,
            int(initial["tick_rotation_airline"]),
            TICK_ROTATION_STEP,
        )

    tuned = collect_tuned_values(ui)
    left_col, right_col = st.columns([1.35, 0.95])

    png_bytes = b""

    with left_col:
        st.subheader("Preview")
        try:
            figure = render_active_chart(tuned)
            png_bytes = fig_to_png_bytes(figure)
            st.image(png_bytes, width="stretch")
        except Exception as exc:
            st.error(f"Preview error: {exc}")

    with right_col:
        st.subheader("Current token values")
        st.dataframe(tuned_values_to_table(tuned), width="stretch", hide_index=True)

        st.subheader("Actions")
        if st.button("Save to visualization_guide.json", width="stretch"):
            guide.setdefault("_tuned_token_values", {})
            for key, value in tuned.items():
                guide["_tuned_token_values"][key] = value

            guide["x_tick_rotation"] = tuned["tick_rotation_airline"]
            save_guide(guide)
            load_guide.clear()
            st.success("Guide saved.")

        st.download_button(
            "Download preview PNG",
            data=png_bytes,
            file_name="faa_chart_preview.png",
            mime="image/png",
            width="stretch",
        )

        if GUIDE_PATH.exists():
            st.download_button(
                "Download visualization_guide.json",
                data=GUIDE_PATH.read_bytes(),
                file_name="visualization_guide.json",
                mime="application/json",
                width="stretch",
            )

    st.divider()
    st.subheader("Notes")
    st.markdown(
        "- The app previews the active airline delay chart.\n"
        "- Saved values are written to `_tuned_token_values` in `visualization_guide.json`.\n"
        "- `X tick rotation` lets you flatten airline labels to reduce overlap.\n"
        "- The header uses the logo instead of a text label."
    )


if __name__ == "__main__":
    main()