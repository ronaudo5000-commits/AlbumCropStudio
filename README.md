# AlbumCrop Studio

**写真を切り出し、記録を未来へつなぐ**

AlbumCrop Studio is a desktop application for detecting and cropping
individual photographs from scanned album pages.

It is designed not only as a photo-cropping tool, but also as a starting
point for organizing, preserving, and sharing historical photographic
records.

> This project is currently in beta.

## Current Version

`0.10.0-beta.1`

## Features

- Load image files and PDF documents
- Automatically detect photographs on scanned album pages
- Create crop frames manually
- Move, resize, copy, rotate, and delete crop frames
- Undo and redo editing operations
- Work with multiple pages
- Save and reopen project files
- Configure output DPI
- Configure crop margins in millimeters
- Configure JPEG quality
- Export cropped photographs as JPEG files
- Preserve crop frames after export
- Confirm before overwriting existing files

## Supported Platforms

- Windows 10
- Windows 11
- macOS

The current beta version is primarily developed and tested on Windows 11.
macOS support is planned, but may require additional testing.

## Technology Stack

- Python
- PySide6
- OpenCV
- Pillow
- NumPy
- PyMuPDF

## Running from Source

### 1. Clone the repository

```bash
git clone https://github.com/ronaudo5000-commits/AlbumCropStudio.git
cd AlbumCropStudio
```

### 2. Create a virtual environment

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Start the application

```bash
python main.py
```

## Basic Workflow

1. Open an image or PDF document.
2. Run automatic photo detection, or create crop frames manually.
3. Adjust the position, size, and rotation of each frame.
4. Open Settings to configure DPI, margin, and JPEG quality.
5. Choose an output folder.
6. Export the cropped photographs.

## Project Files

AlbumCrop Studio can save the current work as a project file.

A saved project can contain information such as:

- Loaded pages
- Crop-frame positions
- Crop-frame sizes
- Rotation angles
- Output settings

Keep the original image and PDF files available when reopening a project.

## Beta Notice

This is a beta release intended for testing and evaluation.

Before processing important or irreplaceable archival material:

- Keep the original files unchanged
- Create backups
- Test the output with sample files
- Check all exported photographs manually

The detection result may require manual adjustment depending on the album
layout, image quality, background, shadows, decorations, or damaged pages.

## Known Limitations

- Automatic detection may not identify every photograph correctly
- Overlapping photographs may require manual frame creation
- Decorative borders and page backgrounds may affect detection
- Very large images and PDFs may require significant memory
- macOS has not yet received the same level of testing as Windows 11
- The interface is currently primarily intended for Japanese-language use
- Advanced metadata and geolocation features are not included in this beta

## Development Philosophy

AlbumCrop Studio aims to support more than image extraction.

The long-term goal is to help build accessible digital archives that can
support historical research, international collaboration, and dialogue
around photographic records.

Future development may include tools for organizing contextual information,
recording uncertain location evidence, and working with additional media
formats.

## Reporting Issues

When reporting a problem, please include:

- AlbumCrop Studio version
- Operating-system version
- Image or PDF format
- Steps needed to reproduce the problem
- What you expected to happen
- What actually happened
- Relevant log information, when available

Please use the GitHub Issues page for bug reports and feature requests.

## License

This project is licensed under the MIT License.

See the `LICENSE` file for details.