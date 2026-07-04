# Installation

## Requirements

Pixel Pattern Generator requires:

- Python 3.11 or newer
- The Python packages listed in `requirements.txt`

<br>

## 1. Download the Project

Clone the repository or download it as a ZIP file and extract it to your computer.

<br>

## 2. Install Required Python Packages

Open a terminal in the project directory and install the required packages:

```bash
pip install -r requirements.txt
```

If your system uses `pip3`, use:

```bash
pip3 install -r requirements.txt
```

<br>

## 3. Prepare the Project

### `palette.csv`

The software uses a user-defined material palette supplied as a CSV file.

By default, the program looks for a file named:

```text
palette.csv
```

The file should be located in the project directory (the same folder as the Python script).

The CSV must contain the following columns:

| Name | R | G | B |
|------|--:|--:|--:|
| White | 255 | 255 | 255 |
| Black | 0 | 0 | 0 |
| Red | 212 | 45 | 63 |

Additional columns may be included but are ignored by the software.

If your palette file has a different filename, the program will prompt you to enter it when it starts.

<br>

### `input_images`

Place one or more source images into the `input_images` folder.

Supported image formats:

- `.png`

- `.jpg`

- `.jpeg`

If the folder does not already exist, it will be created automatically the first time the program is run.

Each compatible image in the folder will be processed automatically.

<br>

### `output_patterns`

All generated files are written to the `output_patterns` folder.

If the folder does not already exist, it will be created automatically.

For each source image, the software generates:

- Printable PDF pattern
- Pattern preview image (`.png`)
- Material count (`.csv`)

When multiple images are processed, the software also generates:

- Global material inventory (`global_materials.csv`)
- Global material summary (`global_materials_summary.csv`)

<br>

## 4. Run the Program

From the project directory, run:

```bash
python pixel_pattern_generator.py
```

or

```bash
python3 pixel_pattern_generator.py
```

The program will prompt you to:

1. Enter the material palette filename (or press Enter to use `palette.csv`)
2. Enter the desired output width (in units)
3. Enter the desired output height (in units)

Every compatible image in input_images will be processed during the same run.

<br>

## Output

Generated files are written automatically to the `output_patterns` folder.

For each source image, the software produces:

- Printable PDF pattern
- Pattern preview image (`.png`)
- Material count (`.csv`)

When multiple images are processed, the software also generates:

* Collection-wide material inventory (global_materials.csv)
* Collection-wide material summary (global_materials_summary.csv)

If the output folder does not already exist, it will be created automatically.

<br>

## Notes

- The program warns before generating very large patterns, which may require substantial processing time, produce large PDF files, or fail on some systems.
- The software preserves transparent pixels when present in PNG images.
- Material colours are supplied by the user through a CSV file, allowing the software to be used with a wide range of fabrication media.