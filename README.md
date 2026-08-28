# AlbumCrop Studio

「資料」を「資源」に そして「資産」へ

AlbumCrop Studio is a desktop application for detecting and cropping
individual photographs from scanned album pages.

It is designed not only as a photo-cropping tool, but also as a starting
point for organizing, preserving, and sharing historical photographic
records.

This repository contains **AlbumCrop Studio Free**, the free edition of
AlbumCrop Studio.

## Current Version

`0.10.0`

## Free Edition Limits

AlbumCrop Studio Free is intended for individual and small-scale archival
workflows.

The Free edition has the following limits:

- Up to **5 pages** can be loaded at one time
- PDF pages are counted individually toward the 5-page limit
- Project files containing more than 5 pages cannot be opened in the Free edition
- Export is limited to **one selected page at a time**
- All crop frames on that selected page can be exported together

Crop-frame editing, automatic detection, project saving, and the other
core editing features remain available within these limits.

## Features

- Load image files and PDF documents
- Automatically detect photographs on scanned album pages
- Create crop frames manually
- Select multiple crop frames
- Select all crop frames on the current page with Ctrl+A
- Move and delete multiple selected crop frames together
- Copy, cut, and paste multiple crop frames while preserving their relative layout
- Copy or move crop-frame layouts between different pages during the same session
- Scale pasted crop-frame layouts proportionally when the source and destination page dimensions differ
- Move, resize, copy, rotate, and delete individual crop frames
- Set an aspect-ratio mode for each crop frame
- Use free resizing, preserve the current ratio, or select a preset ratio
- Choose from 16:9, 9:16, 4:3, 3:2, and 1:1 presets
- Preserve per-frame aspect-ratio settings across page changes, undo and redo, project saving and loading, and export
- Hold Shift while resizing to temporarily preserve the frame's current ratio
- Use compact resize handles with a reduced hit area for easier work with closely spaced crop frames
- Undo and redo editing operations
- Work with multiple pages within the Free edition's 5-page limit
- Switch the page list between thumbnail and compact display modes
- Select one page as the export target
- Save and reopen project files
- Preserve page export selections in project files
- Configure output DPI
- Configure crop margins in millimeters
- Configure JPEG quality
- Preview cropped photographs fitted to the available preview-pane width
- Click a crop preview to open a larger viewer
- Zoom and pan inside the enlarged crop-preview viewer
- Pan the main canvas with the middle mouse button or Space + left drag
- Export all crop frames from one selected page as JPEG files
- Show both percentage and processed/total crop counts during export
- Preserve original page numbers in exported filenames
- Preserve crop frames after export
- Confirm before overwriting existing files
- Cache recently viewed pages for faster page switching

## Supported Platforms

### Officially Supported

- Windows 10
- Windows 11

AlbumCrop Studio Free is primarily developed and tested on Windows 11.

### Planned

- macOS

macOS support is planned, but it has not yet received the same level of
testing as the Windows version.

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
4. Choose free resizing, preserve the frame's current ratio, or select a preset aspect ratio for each frame.
5. Hold Shift while resizing when you want to temporarily preserve the frame's current ratio.
6. Use Ctrl-click to select multiple crop frames, or Ctrl+A to select all crop frames on the current page.
7. Use Ctrl+C to copy or Ctrl+X to cut selected crop frames, then Ctrl+V to paste them while preserving their relative layout.
8. Copy or move crop-frame layouts to another page when needed.
9. Switch the page list between thumbnail and compact modes when working with multiple pages.
10. Check cropped results in the preview pane.
11. Click a crop preview when you need a larger zoomable view.
12. Check one page in the page list as the export target.
13. Configure DPI, margin, and JPEG quality from the main window or Settings.
14. Choose an output folder.
15. Export all crop frames from the selected page.
16. To export another page, select that page as the export target and run export again.

## Project Files

AlbumCrop Studio can save the current work as a project file.

A saved project can contain information such as:

- Loaded pages
- Crop-frame positions
- Crop-frame sizes
- Rotation angles
- Per-frame aspect-ratio modes
- Page export selections
- Output settings

Aspect-ratio modes are stored separately for each crop frame. Projects created
before this feature was added remain compatible; frames without saved ratio
information are opened in free-resize mode.

AlbumCrop Studio Free can open projects containing up to 5 pages.

Projects containing more than 5 pages are not opened in the Free edition in
order to avoid unintentionally loading or overwriting only part of a larger
project.

Keep the original image and PDF files available in their original locations
when reopening a project.

## Important Notes

Before processing important or irreplaceable archival material:

- Keep the original files unchanged
- Create backups
- Test the output with sample files
- Check exported photographs manually when accuracy is important

Automatic detection may require manual adjustment depending on the album
layout, image quality, background, shadows, decorations, or damaged pages.

## Known Limitations

- The Free edition can load up to 5 pages at one time
- The Free edition exports one selected page at a time
- Automatic detection may not identify every photograph correctly
- Overlapping photographs may require manual frame creation
- Decorative borders and page backgrounds may affect detection
- Very large images and PDFs may require significant memory
- Only a limited number of recently viewed pages are cached in memory
- macOS has not yet received the same level of testing as Windows 11
- The interface is currently primarily intended for Japanese-language use
- Advanced metadata and geolocation features are not included in AlbumCrop Studio Free

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