"""
Pixel Pattern Generator
Version 1.0

Description:
    Pixel Pattern Generator converts digital raster images into
    fabrication-ready patterns for colour-limited materials.

    The software reduces an input image to a user-defined grid,
    maps each pixel to the closest available colour contained in a
    user-supplied material palette (CSV), and generates printable
    pattern documentation together with material counts.

Applications:
    • Glass seed beads
    • Quilt blocks
    • Mosaic tiles
    • LEGO
    • Pixel art
    • Other colour-limited fabrication media

Repository:
    https://github.com/sPong888/PixelPatternGenerator


"""

import os
import csv
import math
import re
from PIL import Image
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle

# === PATHS ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_PALETTE_CSV = "palette.csv"
INPUT_FOLDER = os.path.join(SCRIPT_DIR, "input_images")
OUTPUT_FOLDER = os.path.join(SCRIPT_DIR, "output_patterns")

# === SETTINGS ===
MAX_INSTRUCTIONS_PER_LINE = 50
LARGE_PATTERN_WARNING_UNITS = 40000


# === USER INPUT ===
def get_positive_int(prompt):
    while True:
        try:
            value = int(input(prompt).strip())
            if value > 0:
                return value
            print("Please enter a positive whole number.")
        except ValueError:
            print("Please enter a positive whole number.")

def get_pattern_size():
    while True:
        width = get_positive_int("Enter desired width in units: ")
        height = get_positive_int("Enter desired height in units: ")

        total_units = width * height

        if total_units <= LARGE_PATTERN_WARNING_UNITS:
            return width, height

        print(f"\nWarning: The requested pattern contains {total_units:,} units.")
        print("Large patterns may require considerable processing time")
        print("and may produce very large PDF files (or might fail completely!).")
        print("Consider starting small (e.g. 10x10 units) and scaling up gradually.")

        response = input(
            "\nContinue with these dimensions? (y to continue / n to enter new dimensions): "
        ).strip().lower()

        if response == "y":
            return width, height

        print()


def get_palette_path():
    palette_name = input(
        f"Enter palette CSV filename (default: {DEFAULT_PALETTE_CSV}): "
    ).strip()

    if not palette_name:
        palette_name = DEFAULT_PALETTE_CSV

    palette_path = os.path.join(SCRIPT_DIR, palette_name)

    if not os.path.exists(palette_path):
        raise FileNotFoundError(
            f"\nError: {palette_name} could not be found.\n"
            f"Place the palette CSV file in the same directory as this script and try again."
        )

    return palette_path, palette_name


palette_path, palette_filename = get_palette_path()

desired_width_units, desired_height_units = get_pattern_size()
#desired_width_units = get_positive_int("Enter desired width in units: ")
#desired_height_units = get_positive_int("Enter desired height in units: ")
print("Working...")


# === LOAD PALETTE ===
def load_material_palette(csv_path):
    palette = {"Transparent": (0, 0, 0, 0)}

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        required_columns = {"Name", "R", "G", "B"}
        missing_columns = required_columns - set(reader.fieldnames or [])

        if missing_columns:
            raise ValueError(
                f"Palette CSV is missing required column(s): {', '.join(missing_columns)}"
            )

        for row in reader:
            name = row["Name"]
            rgb = (int(row["R"]), int(row["G"]), int(row["B"]))
            palette[name] = rgb

    return palette


# === COLOUR CONVERSION ===
def _srgb_to_linear(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def rgb_to_lab(rgb):
    """Convert sRGB (0–255) to CIE L*a*b*."""
    r, g, b = [_srgb_to_linear(v) for v in rgb[:3]]

    x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041

    Xn, Yn, Zn = 0.95047, 1.0, 1.08883
    x, y, z = x / Xn, y / Yn, z / Zn

    def f(t):
        return t ** (1 / 3) if t > 0.008856 else (7.787 * t + 16 / 116)

    fx, fy, fz = f(x), f(y), f(z)

    return (
        116 * fy - 16,
        500 * (fx - fy),
        200 * (fy - fz),
    )


def lab_dist2(lab_1, lab_2):
    return (
        (lab_1[0] - lab_2[0]) ** 2
        + (lab_1[1] - lab_2[1]) ** 2
        + (lab_1[2] - lab_2[2]) ** 2
    )


def build_palette_index(palette):
    index = []

    for name, rgb in palette.items():
        if name == "Transparent":
            continue

        index.append(
            {
                "name": name,
                "rgb": rgb,
                "lab": rgb_to_lab(rgb),
            }
        )

    return index


# === COLOUR MATCHING ===
# Colour matching is performed in CIE L*a*b* colour space
# using squared Euclidean distance, which more closely
# approximates human colour perception than direct RGB
# distance calculations.
"""

    Load a user-defined material palette from a CSV file.

    Required columns:

        Name, R, G, B

    Returns:

        dict mapping material names to RGB tuples.

    """
def closest_color(rgb, palette_index):
    pix_lab = rgb_to_lab(rgb)

    best_name = None
    best_d = float("inf")

    for material in palette_index:
        d = lab_dist2(pix_lab, material["lab"])
        if d < best_d:
            best_d = d
            best_name = material["name"]

    return best_name


# === ROW INSTRUCTIONS ===
def compress_row(row, color_to_num):
    row = row.tolist()

    if not row:
        return []

    result = []
    prev = row[0]
    count = 1

    for color in row[1:]:
        if color == prev:
            count += 1
        else:
            result.append(
                f"{count}x{color_to_num[prev]}"
                if count > 1
                else f"{color_to_num[prev]}"
            )
            prev = color
            count = 1

    result.append(
        f"{count}x{color_to_num[prev]}"
        if count > 1
        else f"{color_to_num[prev]}"
    )

    return result


# === PDF OUTPUT ===
def create_pdf(
    name,
    output_dir,
    mapped_grid,
    color_counts,
    palette,
    orig_img,
    pattern_img,
    original_size,
    palette_filename,
):
    h, w = mapped_grid.shape
    original_w, original_h = original_size

    used_colors = [c for c in palette if color_counts.get(c, 0) > 0]

    color_to_num = {"Transparent": 0} if "Transparent" in used_colors else {}
    non_transparent = [c for c in used_colors if c != "Transparent"]
    color_to_num.update({c: i + 1 for i, c in enumerate(non_transparent)})

    pdf_path = os.path.join(output_dir, f"{name}.pdf")

    with PdfPages(pdf_path) as pdf:
        # PAGE 1: SUMMARY
        fig, ax = plt.subplots(figsize=(8.5, 11))
        ax.axis("off")

        ax.text(
            0.05,
            1.01,
            f"Pattern Summary: {name}",
            fontsize=12,
            fontweight="bold",
            transform=ax.transAxes,
        )

        orig_thumb = orig_img.resize((300, 300))
        pattern_thumb = pattern_img.resize((300, 300))

        fig.figimage(orig_thumb, xo=70, yo=600)
        fig.figimage(pattern_thumb, xo=400, yo=600)

        ax.text(0.10, 0.55, "Original Image", fontsize=10, transform=ax.transAxes)
        ax.text(
            0.50,
            0.55,
            "Colour & Resolution Preview",
            fontsize=10,
            transform=ax.transAxes,
        )

        total_units = sum(color_counts.values())

        reduction_w = original_w / w
        reduction_h = original_h / h

        lines = [
            f"Original image size: {original_w} x {original_h} pixels",
            f"Output grid size: {w} x {h} units",
            f"Approx. reduction ratio: {reduction_w:.2f}:1 width, {reduction_h:.2f}:1 height",
            f"Total units: {total_units}",
            f"Colours used: {len(used_colors)}",
            f"Palette file: {palette_filename}",
        ]

        for i, line in enumerate(lines):
            ax.text(0.05, 0.48 - i * 0.035, line, fontsize=10, transform=ax.transAxes)

        pdf.savefig()
        plt.close()

        # PAGE 2+: LEGEND + MATERIAL COUNT
        legend_entries = [
            f"{color_to_num[c]}: {c.ljust(40)} {color_counts[c]} units"
            for c in used_colors
        ]

        entries_per_page = 40
        total_pages = math.ceil(len(legend_entries) / entries_per_page)

        for page in range(total_pages):
            fig, ax = plt.subplots(figsize=(8.5, 11))
            ax.axis("off")

            ax.text(
                0.05,
                1.01,
                f"Legend & Material Count – {name} (Page {page + 1})",
                fontsize=12,
                fontweight="bold",
                transform=ax.transAxes,
            )

            page_entries = legend_entries[
                page * entries_per_page : (page + 1) * entries_per_page
            ]

            for i, entry in enumerate(page_entries):
                ax.text(0.05, 0.97 - i * 0.025, entry, fontsize=8, transform=ax.transAxes)

            pdf.savefig()
            plt.close()

        # PAGE 3: PATTERN GRID
        fig, ax = plt.subplots(figsize=(8.5, 11))
        ax.set_xlim(-1, w)
        ax.set_ylim(-1, h + 2)
        ax.set_aspect("equal")
        ax.axis("off")

        ax.text(
            0.05,
            1.01,
            f"Pattern Grid – {name}",
            fontsize=12,
            fontweight="bold",
            transform=ax.transAxes,
        )

        for y in range(h):
            for x in range(w):
                color = mapped_grid[y, x]
                is_transparent = color == "Transparent"

                rgb = (
                    (0.87, 0.87, 0.87)
                    if is_transparent
                    else [v / 255 for v in palette[color]]
                )

                ax.add_patch(Rectangle((x, h - y - 1), 1, 1, color=rgb, linewidth=0))

                num = color_to_num.get(color, "")
                if num != "":
                    brightness = sum(rgb[:3]) / 3
                    text_color = "black" if brightness > 0.6 else "white"

                    ax.text(
                        x + 0.5,
                        h - y - 0.5,
                        str(num),
                        ha="center",
                        va="center",
                        fontsize=8,
                        weight="bold",
                        color=text_color,
                    )

        for x in range(w + 1):
            ax.plot([x, x], [0, h], color="black", linewidth=1.0 if x % 5 == 0 else 0.2)

        for y in range(h + 1):
            ax.plot([0, w], [y, y], color="black", linewidth=1.0 if y % 5 == 0 else 0.2)

        for y in range(h):
            ax.text(
                -0.5,
                h - y - 0.5,
                str(y + 1),
                va="center",
                ha="right",
                fontsize=8,
                weight="bold",
            )

        for x in range(w):
            ax.text(
                x + 0.5,
                h + 0.1,
                str(x + 1),
                ha="center",
                va="bottom",
                fontsize=8,
                weight="bold",
            )

        pdf.savefig()
        plt.close()

        # PAGE 4+: ROW INSTRUCTIONS
        row_blocks = []

        for i, row in enumerate(mapped_grid):
            line = compress_row(row, color_to_num)

            chunks = [
                ", ".join(line[i : i + MAX_INSTRUCTIONS_PER_LINE])
                for i in range(0, len(line), MAX_INSTRUCTIONS_PER_LINE)
            ]

            row_blocks.append((i + 1, chunks))

        rows_per_page = 25

        for start in range(0, len(row_blocks), rows_per_page):
            fig, ax = plt.subplots(figsize=(8.5, 11))
            ax.axis("off")

            page_rows = row_blocks[start : start + rows_per_page]
            page_num = start // rows_per_page + 1

            ax.text(
                0.05,
                1.01,
                f"Row Instructions (Page {page_num}) – {name}",
                fontsize=12,
                fontweight="bold",
                transform=ax.transAxes,
            )

            y = 0.97

            for row_num, lines in page_rows:
                for line in lines:
                    ax.text(
                        0.05,
                        y,
                        f"Row {row_num}: {line}",
                        fontsize=8,
                        transform=ax.transAxes,
                    )
                    y -= 0.035

            pdf.savefig()
            plt.close()


# === PROCESS IMAGE ===
def process_image(
    image_path,
    output_dir,
    palette,
    palette_index,
    desired_width_units,
    desired_height_units,
    palette_filename,
):
    os.makedirs(output_dir, exist_ok=True)

    name = os.path.splitext(os.path.basename(image_path))[0]

    img = Image.open(image_path).convert("RGBA")
    orig_img = img.copy()
    original_size = img.size

    img = img.resize((desired_width_units, desired_height_units), Image.NEAREST)

    pixels = np.array(img)
    h, w = pixels.shape[:2]

    mapped_grid = np.empty((h, w), dtype=object)
    color_counts = {c: 0 for c in palette}
    color_counts["Transparent"] = 0

    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[y, x]

            if a == 0:
                mapped_grid[y, x] = "Transparent"
                color_counts["Transparent"] += 1
            else:
                color = closest_color((r, g, b), palette_index)
                mapped_grid[y, x] = color
                color_counts[color] += 1

    pattern_img = Image.new("RGB", (w, h))

    for y in range(h):
        for x in range(w):
            c = mapped_grid[y, x]
            pattern_img.putpixel(
                (x, y),
                (220, 220, 220) if c == "Transparent" else palette[c],
            )

    pattern_img_large = pattern_img.resize((w * 20, h * 20), Image.NEAREST)
    pattern_img_large.save(os.path.join(output_dir, f"{name}_pattern.png"))

    with open(
        os.path.join(output_dir, f"{name}_materials.csv"),
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.writer(f)
        writer.writerow(["Material Color", "Quantity"])

        for c, count in color_counts.items():
            if count > 0:
                writer.writerow([c, count])

    create_pdf(
        name,
        output_dir,
        mapped_grid,
        color_counts,
        palette,
        orig_img,
        pattern_img_large,
        original_size,
        palette_filename,
    )

    print(f"Pattern and material count saved for {name}")


# === PROCESS FOLDER ===
def process_folder(
    input_dir,
    output_dir,
    palette,
    palette_index,
    desired_width_units,
    desired_height_units,
    palette_filename,
):
    

    if not os.path.exists(input_dir):
        os.makedirs(input_dir)
        print(f"Created missing input folder: {input_dir}")
        print("Add images to this folder and run the program again.")
        return 0
    if not os.path.exists(output_dir):

        os.makedirs(output_dir)

        print(f"Created output folder: {output_dir}")

    processed_count = 0
    


    for filename in os.listdir(input_dir):
        if filename.lower().endswith((".png", ".jpg", ".jpeg")):
            process_image(
                os.path.join(input_dir, filename),
                output_dir,
                palette,
                palette_index,
                desired_width_units,
                desired_height_units,
                palette_filename,
            )
            processed_count += 1

    if processed_count == 0:
        print(f"No compatible image files found in {input_dir}.")

    return processed_count


# === GLOBAL MATERIAL SUMMARY ===
def create_global_material_summary(output_dir):
    global_materials = {}
    total_units_all = 0

    rgb_pattern = re.compile(r"\((\d+),(\d+),(\d+)\)")

    for filename in os.listdir(output_dir):
        if filename.endswith("_materials.csv") and filename != "global_materials.csv":
            image_name = filename.replace("_materials.csv", "")

            with open(os.path.join(output_dir, filename), newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                for row in reader:
                    color_name = row["Material Color"]
                    count = int(row["Quantity"])
                    total_units_all += count

                    rgb_match = rgb_pattern.search(color_name)
                    rgb = tuple(map(int, rgb_match.groups())) if rgb_match else ("", "", "")

                    if color_name not in global_materials:
                        global_materials[color_name] = {
                            "count": 0,
                            "images": set(),
                            "rgb": rgb,
                        }

                    global_materials[color_name]["count"] += count
                    global_materials[color_name]["images"].add(image_name)

    if not global_materials:
        return

    with open(
        os.path.join(output_dir, "global_materials.csv"),
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "Material Color",
                "R",
                "G",
                "B",
                "Image Name",
                "Quantity",
                "Percent of Total Units",
            ]
        )

        for color, data in sorted(global_materials.items(), key=lambda x: -x[1]["count"]):
            r, g, b = data["rgb"]

            for image in sorted(data["images"]):
                materials_path = os.path.join(output_dir, f"{image}_materials.csv")

                if os.path.exists(materials_path):
                    with open(materials_path, newline="", encoding="utf-8") as materials_file:
                        reader = csv.DictReader(materials_file)

                        for row in reader:
                            if row["Material Color"] == color:
                                qty = int(row["Quantity"])
                                pct = (
                                    (qty / total_units_all) * 100
                                    if total_units_all > 0
                                    else 0
                                )
                                writer.writerow(
                                    [color, r, g, b, image, qty, f"{pct:.2f}%"]
                                )
                                break

    with open(
        os.path.join(output_dir, "global_materials_summary.csv"),
        "w",
        newline="",
        encoding="utf-8",
    ) as f_summary:
        writer_summary = csv.writer(f_summary)
        writer_summary.writerow(
            [
                "Material Color",
                "R",
                "G",
                "B",
                "Total Quantity",
                "Percent of Total Units",
            ]
        )

        for color, data in sorted(global_materials.items(), key=lambda x: -x[1]["count"]):
            r, g, b = data["rgb"]
            total_qty = data["count"]
            pct = (total_qty / total_units_all) * 100 if total_units_all > 0 else 0

            writer_summary.writerow([color, r, g, b, total_qty, f"{pct:.2f}%"])

    print(f"Global material summaries saved.")


# === MAIN EXECUTION ===
if __name__ == "__main__":
    try:
        material_palette = load_material_palette(palette_path)
        palette_index = build_palette_index(material_palette)

        processed_count = process_folder(
            INPUT_FOLDER,
            OUTPUT_FOLDER,
            material_palette,
            palette_index,
            desired_width_units,
            desired_height_units,
            palette_filename,
        )

        if processed_count > 0:
            create_global_material_summary(OUTPUT_FOLDER)

            print("\nProcessing complete.")
            print(f"Generated patterns for {processed_count} image(s).")
            print(f"Output saved to: {OUTPUT_FOLDER}")

    except Exception as e:
        print(e)