from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt5.QtGui import QColor, QPalette
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import matplotlib.patches as patches


class AxisPlotWidget(FigureCanvas):
    def __init__(self, parent=None):
        width_px = 1500
        height_px = 580
        dpi = 100
        fig_width_inch = width_px / dpi
        fig_height_inch = height_px / dpi

        self.fig, self.ax = plt.subplots(figsize=(fig_width_inch, fig_height_inch), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        self.draw_plot()

    def draw_plot(self):
        ax = self.ax
        self.fig.subplots_adjust(left=0, right=1, top=1, bottom=0)  # Elimină marginile
        ax.clear()

        plot_width_mm = 700
        plot_height_mm = 300
        pixels_per_mm = 2

        plot_width_px = plot_width_mm * pixels_per_mm
        plot_height_px = plot_height_mm * pixels_per_mm
        half_height_px = plot_height_px // 2
        grid_size_mm = 10

        # Limits
        machine_limit_left_mm = 76
        machine_limit_right_mm = 622
        machine_limit_left_px = machine_limit_left_mm * pixels_per_mm
        machine_limit_right_px = machine_limit_right_mm * pixels_per_mm

        tool_limit_y_positive_mm = 115
        tool_limit_y_positive_px = tool_limit_y_positive_mm * pixels_per_mm

        tool_limit_x_positive_mm = 150
        tool_limit_x_positive_px = tool_limit_x_positive_mm * pixels_per_mm

        outside_padding = 40

        # Colors
        red_color = 'red'
        orange_color = '#ff7f00'
        green_color = 'green'
        black_color = 'black'
        gray_color = '#bbbbbb'
        light_gray_color = '#dcdcdc'
        dash_pattern_center = (3, 3, 6, 6, 3, 3, 3, 3, 6, 6)
        dash_pattern_orange = (4, 2, 4, 6)

        ax.set_facecolor('white')

        outside_padding_x = 100
        outside_padding_y = 80
        ax.set_xlim(-outside_padding_x, plot_width_px + outside_padding_x)
        ax.set_ylim(-outside_padding_y, plot_height_px + outside_padding_y)

        # Green border box (chart perimeter + labels)
        ax.plot([-outside_padding, plot_width_px + outside_padding], [plot_height_px + outside_padding, plot_height_px + outside_padding], color=green_color, linewidth=1)
        ax.plot([-outside_padding, -outside_padding], [-outside_padding, plot_height_px + outside_padding], color=green_color, linewidth=1)
        ax.plot([-outside_padding, plot_width_px + outside_padding], [-outside_padding, -outside_padding], color=green_color, linewidth=1)
        ax.plot([plot_width_px + outside_padding, plot_width_px + outside_padding], [-outside_padding, plot_height_px + outside_padding], color=green_color, linewidth=1)

        # Hashed inactive zones
        def add_hatched_area(x_start, x_end, y_start, y_end, angle_up=True):
            hatch = '///' if angle_up else '\\\\\\'
            rect = patches.Rectangle(
                (x_start, y_start), x_end - x_start, y_end - y_start,
                facecolor='none', edgecolor=light_gray_color, hatch=hatch, linewidth=0, alpha=0.5, zorder=4
            )
            ax.add_patch(rect)

        add_hatched_area(0, machine_limit_left_px, 0, half_height_px, True)
        add_hatched_area(0, machine_limit_left_px, half_height_px, plot_height_px, False)
        add_hatched_area(machine_limit_right_px, plot_width_px, 0, half_height_px, True)
        add_hatched_area(machine_limit_right_px, plot_width_px, half_height_px, plot_height_px, False)
        add_hatched_area(machine_limit_left_px, machine_limit_right_px, half_height_px + tool_limit_y_positive_px, plot_height_px, False)
        add_hatched_area(machine_limit_left_px, machine_limit_right_px, 0, half_height_px - tool_limit_y_positive_px, True)

        # Machine limits lines & boxes in red
        for x, val in [(machine_limit_left_px, machine_limit_left_mm), (machine_limit_right_px, machine_limit_right_mm)]:
            ax.plot([x, x], [0, plot_height_px], color=red_color, linewidth=1)
            ax.plot([x, x], [plot_height_px, plot_height_px + 40], color=red_color, linewidth=1, zorder=10)
            ax.plot([x, x], [0, -40], color=red_color, linewidth=1, zorder=10)
            box_above = patches.FancyBboxPatch(
                (x-25, plot_height_px+40), 50, 24,
                boxstyle="round,pad=0.3,rounding_size=5",
                facecolor='white', edgecolor=red_color, linewidth=1.5, zorder=11
            )
            box_below = patches.FancyBboxPatch(
                (x-25, -64), 50, 24,
                boxstyle="round,pad=0.3,rounding_size=5",
                facecolor='white', edgecolor=red_color, linewidth=1.5, zorder=11
            )
            ax.add_patch(box_above)
            ax.add_patch(box_below)
            ax.text(x, plot_height_px + 52, f"{val}", ha='center', va='center', fontsize=8, color=red_color, fontweight='bold', zorder=12)
            ax.text(x, -52, f"{val}", ha='center', va='center', fontsize=8, color=red_color, fontweight='bold', zorder=12)

        # Center zero dashed line with pattern
        ax.plot([0, plot_width_px], [half_height_px, half_height_px], color=light_gray_color, linewidth=1, linestyle=(0, dash_pattern_center))

        # Tool limits lines and boxes (orange)
        y_upper_pos = half_height_px + tool_limit_y_positive_px
        y_lower_pos = half_height_px - tool_limit_y_positive_px
        x_left_end = -40
        x_right_end = plot_width_px + 40
        for y in [y_upper_pos, y_lower_pos]:
            ax.plot([x_left_end, x_right_end], [y, y], color=orange_color, linewidth=1, linestyle=(0, dash_pattern_orange))

        ax.plot([tool_limit_x_positive_px, tool_limit_x_positive_px], [-40, plot_height_px + 40], color=orange_color, linewidth=1, linestyle=(0, dash_pattern_orange))

        # Orange boxes outside chart for tool limit Y
        box_top_right = patches.FancyBboxPatch((plot_width_px+45, y_upper_pos-12), 40, 24,
                                               boxstyle="round,pad=0.3,rounding_size=5",
                                               facecolor='white', edgecolor=orange_color, linewidth=1.5, zorder=11)
        box_top_left = patches.FancyBboxPatch((-85, y_upper_pos-12), 40, 24,
                                              boxstyle="round,pad=0.3,rounding_size=5",
                                              facecolor='white', edgecolor=orange_color, linewidth=1.5, zorder=11)
        box_bottom_right = patches.FancyBboxPatch((plot_width_px+45, y_lower_pos-12), 40, 24,
                                                  boxstyle="round,pad=0.3,rounding_size=5",
                                                  facecolor='white', edgecolor=orange_color, linewidth=1.5, zorder=11)
        box_bottom_left = patches.FancyBboxPatch((-85, y_lower_pos-12), 40, 24,
                                                 boxstyle="round,pad=0.3,rounding_size=5",
                                                 facecolor='white', edgecolor=orange_color, linewidth=1.5, zorder=11)

        for box in [box_top_right, box_top_left, box_bottom_right, box_bottom_left]:
            ax.add_patch(box)

        ax.text(plot_width_px + 65, y_upper_pos + 1, f"{tool_limit_y_positive_mm}", ha='center', va='center', fontsize=8, color=orange_color, fontweight='bold', zorder=12)
        ax.text(-65, y_upper_pos + 1, f"{tool_limit_y_positive_mm}", ha='center', va='center', fontsize=8, color=orange_color, fontweight='bold', zorder=12)
        ax.text(plot_width_px + 65, y_lower_pos + 1, f"{tool_limit_y_positive_mm}", ha='center', va='center', fontsize=8, color=orange_color, fontweight='bold', zorder=12)
        ax.text(-65, y_lower_pos + 1, f"{tool_limit_y_positive_mm}", ha='center', va='center', fontsize=8, color=orange_color, fontweight='bold', zorder=12)

        # Solid orange boxes with white text inside chart
        box_center_x = (machine_limit_left_px + machine_limit_right_px) / 2
        box_width = 90
        box_height = 30

        solid_box_top = patches.FancyBboxPatch((box_center_x - box_width/2, y_upper_pos - box_height/2), box_width, box_height,
                                               boxstyle="round,pad=0.5,rounding_size=6",
                                               facecolor=orange_color, edgecolor=orange_color, zorder=8)
        solid_box_bottom = patches.FancyBboxPatch((box_center_x - box_width/2, y_lower_pos - box_height/2), box_width, box_height,
                                                  boxstyle="round,pad=0.5,rounding_size=6",
                                                  facecolor=orange_color, edgecolor=orange_color, zorder=8)

        ax.add_patch(solid_box_top)
        ax.add_patch(solid_box_bottom)
        ax.text(box_center_x, y_upper_pos, "200.231", color='white', fontsize=10, fontweight='bold', ha='center', va='center', zorder=9)
        ax.text(box_center_x, y_lower_pos, "200.231", color='white', fontsize=10, fontweight='bold', ha='center', va='center', zorder=9)

        # Grid lines and ticks on X axis (0-700 mm)
        for x in range(0, plot_width_px + 1, grid_size_mm * pixels_per_mm):
            if x > plot_width_px:
                continue
            length = 5
            active = machine_limit_left_px <= x <= machine_limit_right_px
            color = black_color if active else gray_color
            if x % (100 * pixels_per_mm) == 0:
                length = 15
                label = str(x // (100 * pixels_per_mm) * 100)
                ax.text(x, plot_height_px + 10, label, ha='center', va='bottom', fontsize=8, color=color)
                ax.text(x, -10, label, ha='center', va='top', fontsize=8, color=color)
            elif x % (50 * pixels_per_mm) == 0:
                length = 10
            ax.plot([x, x], [0, length], color=color, linewidth=1)
            ax.plot([x, x], [plot_height_px, plot_height_px - length], color=color, linewidth=1)

        # Grid lines and ticks on Y axis (+/-150mm)
        for y in range(0, half_height_px + 1, grid_size_mm * pixels_per_mm):
            length = 5
            # Positive side
            y_pos = half_height_px + y
            active = (half_height_px - tool_limit_y_positive_px) <= y_pos <= (half_height_px + tool_limit_y_positive_px)
            color = black_color if active else gray_color
            if y % (50 * pixels_per_mm) == 0 or y == 0:
                length = 15
                label = str(abs(int((y_pos - half_height_px) / pixels_per_mm)))
                ax.text(-10, y_pos, label, ha='right', va='center', fontsize=8, color=color)
                ax.text(plot_width_px + 10, y_pos, label, ha='left', va='center', fontsize=8, color=color)
            ax.plot([0, length], [y_pos, y_pos], color=color, linewidth=1)
            ax.plot([plot_width_px, plot_width_px - length], [y_pos, y_pos], color=color, linewidth=1)
            # Negative side
            y_neg = half_height_px - y
            active = (half_height_px - tool_limit_y_positive_px) <= y_neg <= (half_height_px + tool_limit_y_positive_px)
            color = black_color if active else gray_color
            if y % (50 * pixels_per_mm) == 0 or y == 0:
                length = 15
                label = str(abs(int((y_neg - half_height_px) / pixels_per_mm)))
                ax.text(-10, y_neg, label, ha='right', va='center', fontsize=8, color=color)
                ax.text(plot_width_px + 10, y_neg, label, ha='left', va='center', fontsize=8, color=color)
            ax.plot([0, length], [y_neg, y_neg], color=color, linewidth=1)
            ax.plot([plot_width_px, plot_width_px - length], [y_neg, y_neg], color=color, linewidth=1)

        # Zero labels
        ax.text(-10, half_height_px, "0", ha='right', va='center', fontsize=8, color=black_color)
        ax.text(plot_width_px + 10, half_height_px, "0", ha='left', va='center', fontsize=8, color=black_color)

        ax.axis('off')
        self.draw()


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication, QMainWindow

    app = QApplication(sys.argv)

    # Creează fereastra principală
    win = QMainWindow()
    win.resize(1500, 580)
    win.setWindowTitle("AxisPlot Widget with Pink Background")

    # Setează un background roz pentru fereastră
    pal = win.palette()
    pal.setColor(QPalette.Window, QColor(255, 192, 203))  # Pink
    win.setPalette(pal)
    win.setAutoFillBackground(True)

    # Adaugă widgetul AxisPlotWidget
    widget = AxisPlotWidget()
    win.setCentralWidget(widget)

    win.show()
    sys.exit(app.exec_())
