import json
import copy
import tkinter as tk
from tkinter import ttk, messagebox

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import visualizations

GUIDE_PATH = "visualization_guide.json"
TARGET_TOKEN_NAMES = [
    "header_standard",
    "logo_standard",
    "margins_chart_rotated_labels",
    "title_under_header",
    "subtitle_under_title",
    "footer_bottom_right",
    "tick_rotation_airline",
]

INITIAL_TOKEN_VALUES = {
    "header_standard": 0.12,
    "logo_standard": [0.014, 0.872, 0.05, 0.08],
    "margins_chart_rotated_labels": {
        "left": 0.07,
        "right": 0.985,
        "top": 0.78,
        "bottom": 0.16,
    },
    "title_under_header": {"x": 0.08, "y": 0.835},
    "subtitle_under_title": {"x": 0.08, "y": 0.798},
    "footer_bottom_right": {"x": 0.985, "y": 0.02},
    "tick_rotation_airline": 65,
}


class GuideTunerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Visualization Guide Tuner")
        self.values = copy.deepcopy(INITIAL_TOKEN_VALUES)
        self.variables = {}
        self.canvas = None
        self.build_ui()

    def build_ui(self):
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        controls = ttk.Frame(self.root, padding=12)
        controls.grid(row=0, column=0, sticky="nsw")

        preview = ttk.Frame(self.root, padding=12)
        preview.grid(row=0, column=1, sticky="nsew")
        preview.rowconfigure(0, weight=1)
        preview.columnconfigure(0, weight=1)
        self.preview_frame = preview

        row = 0
        ttk.Label(
            controls,
            text="Adjust token values for visualization layout",
            font=("Arial", 12, "bold")
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 10))
        row += 1

        fields = [
            ("header_standard", "Header height", self.values["header_standard"]),
            ("logo_x", "Logo x", self.values["logo_standard"][0]),
            ("logo_y", "Logo y", self.values["logo_standard"][1]),
            ("logo_w", "Logo width", self.values["logo_standard"][2]),
            ("logo_h", "Logo height", self.values["logo_standard"][3]),
            ("margin_left", "Margin left", self.values["margins_chart_rotated_labels"]["left"]),
            ("margin_right", "Margin right", self.values["margins_chart_rotated_labels"]["right"]),
            ("margin_top", "Margin top", self.values["margins_chart_rotated_labels"]["top"]),
            ("margin_bottom", "Margin bottom", self.values["margins_chart_rotated_labels"]["bottom"]),
            ("title_x", "Title x", self.values["title_under_header"]["x"]),
            ("title_y", "Title y", self.values["title_under_header"]["y"]),
            ("subtitle_x", "Subtitle x", self.values["subtitle_under_title"]["x"]),
            ("subtitle_y", "Subtitle y", self.values["subtitle_under_title"]["y"]),
            ("footer_x", "Footer x", self.values["footer_bottom_right"]["x"]),
            ("footer_y", "Footer y", self.values["footer_bottom_right"]["y"]),
            ("tick_rotation_airline", "X tick rotation", self.values["tick_rotation_airline"]),
        ]

        for key, label, value in fields:
            ttk.Label(controls, text=label).grid(row=row, column=0, sticky="w", pady=2)
            var = tk.DoubleVar(value=value)
            self.variables[key] = var
            entry = ttk.Entry(controls, textvariable=var, width=12)
            entry.grid(row=row, column=1, sticky="w", padx=(8, 0), pady=2)
            entry.bind("<KeyRelease>", lambda event: self.schedule_preview())
            row += 1

        button_frame = ttk.Frame(controls)
        button_frame.grid(row=row, column=0, columnspan=2, sticky="w", pady=(12, 0))

        ttk.Button(button_frame, text="Preview active chart", command=self.update_preview).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(button_frame, text="Save token values to JSON", command=self.save_to_json).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(button_frame, text="Print values", command=self.print_values).grid(row=0, column=2)

        self.update_preview()

    def schedule_preview(self):
        self.root.after(150, self.update_preview)

    def collect_values(self):
        return {
            "header_standard": self.variables["header_standard"].get(),
            "logo_standard": [
                self.variables["logo_x"].get(),
                self.variables["logo_y"].get(),
                self.variables["logo_w"].get(),
                self.variables["logo_h"].get(),
            ],
            "margins_chart_rotated_labels": {
                "left": self.variables["margin_left"].get(),
                "right": self.variables["margin_right"].get(),
                "top": self.variables["margin_top"].get(),
                "bottom": self.variables["margin_bottom"].get(),
            },
            "title_under_header": {
                "x": self.variables["title_x"].get(),
                "y": self.variables["title_y"].get(),
            },
            "subtitle_under_title": {
                "x": self.variables["subtitle_x"].get(),
                "y": self.variables["subtitle_y"].get(),
            },
            "footer_bottom_right": {
                "x": self.variables["footer_x"].get(),
                "y": self.variables["footer_y"].get(),
            },
            "tick_rotation_airline": self.variables["tick_rotation_airline"].get(),
        }

    def update_preview(self):
        try:
            tuned = self.collect_values()

            chart = visualizations.AirlineDelayBarChart()
            visualizations.deep_update(chart.guide, visualizations.resolve_token(tuned))
            chart.guide["x_tick_rotation"] = tuned["tick_rotation_airline"]

            fig = chart.build_figure()

            if self.canvas is not None:
                self.canvas.get_tk_widget().destroy()
                self.canvas = None

            self.canvas = FigureCanvasTkAgg(fig, master=self.preview_frame)
            widget = self.canvas.get_tk_widget()
            widget.grid(row=0, column=0, sticky="nsew")

            self.canvas.draw_idle()
            self.preview_frame.update_idletasks()

        except Exception as exc:
            print("Preview error:", exc)

    def save_to_json(self):
        try:
            with open(GUIDE_PATH, "r", encoding="utf-8") as f:
                guide = json.load(f)

            tuned = self.collect_values()
            guide.setdefault("_tuned_token_values", {})
            for token_name in TARGET_TOKEN_NAMES:
                guide["_tuned_token_values"][token_name] = tuned[token_name]

            guide["x_tick_rotation"] = tuned["tick_rotation_airline"]

            with open(GUIDE_PATH, "w", encoding="utf-8") as f:
                json.dump(guide, f, indent=2)

            messagebox.showinfo("Saved", f"Saved tuned token values to {GUIDE_PATH}.")

        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def print_values(self):
        print(json.dumps(self.collect_values(), indent=2))


if __name__ == "__main__":
    root = tk.Tk()
    app = GuideTunerApp(root)
    root.mainloop()