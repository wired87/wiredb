
import numpy as np
import matplotlib.pyplot as plt



class Plotter:


    """
    Create plots of

    """

    def __init__(self):
        self.fig, self.ax = plt.subplots()

    def main(self):

    def _plot_field_values(self, item_history: list):
        """
        Plots field values over time from item_history.
        Each item in item_history should be a dict with 't' (time) and 'value'.
        """
        if not item_history:
            print("No admin_data to plot.")
            return

        times = [item["t"] for item in item_history]
        values = [item["value"] for item in item_history]

        plt.figure(figsize=(6, 4))
        plt.plot(times, values, marker='o')
        plt.xlabel("Time")
        plt.ylabel("Field Value")
        plt.title("Field Value over Time")
        plt.grid(True)
        plt.tight_layout()
        plt.show()