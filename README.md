# AlbumCrop Studio

[English](README.md) | [日本語](docs/README_ja.md) | [繁體中文](docs/README_zh_TW.md)

「資料」を「資源」に そして「資産」へ

AlbumCrop Studio is a desktop application for detecting and cropping individual photographs from scanned album pages and other archival image materials.

It is designed not only as a photo-cropping tool, but also as a starting point for organizing, preserving, reusing, and sharing historical photographic records.

This repository contains **AlbumCrop Studio Free**, the free edition of AlbumCrop Studio.

## Current Stable Release

`0.11.0`

The main development branch may contain features and improvements that are not yet included in the latest stable release.

## Free Edition Limits

AlbumCrop Studio Free is intended for individual and small-scale archival workflows.

The Free edition has the following limits:

- Up to **5 pages** can be loaded at one time
- PDF pages are counted individually toward the 5-page limit
- Project files containing more than 5 pages cannot be opened in the Free edition
- Export is limited to **one selected page at a time**
- All crop frames on that selected page can be exported together

Crop-frame editing, automatic detection, project saving, recovery support, mosaic masking, and the other core editing features remain available within these limits.

## Features

### Loading and Page Management

- Load image files and PDF documents
- Work with multiple pages within the Free edition's 5-page limit
- Switch the page list between thumbnail and compact display modes
- Select one page as the export target
- Delete pages and restore deleted pages with Undo
- Cache recently viewed pages for faster page switching

### Crop Frames

- Automatically detect photographs on scanned album pages
- Create crop frames manually
- Move, resize, copy, rotate, and delete individual crop frames
- Select multiple crop frames
- Select all crop frames on the current page with Ctrl+A
- Move and delete multiple selected crop frames together
- Copy, cut, and paste multiple crop frames while preserving their relative layout
- Copy or move crop-frame layouts between different pages during the same session
- Paste crop-frame layouts to selected pages or all other loaded pages
- Scale pasted crop-frame layouts proportionally when the source and destination page dimensions differ
- Preserve existing mosaic frames when crop-frame layouts are pasted to other pages
- Undo and redo editing operations
- Undo and redo multi-page crop-frame paste operations

### Alignment and Distribution

Multiple independent crop frames can be aligned or distributed directly from the context menu.

Available alignment operations include:

- Align Left
- Align Horizontal Centers
- Align Right
- Align Top
- Align Vertical Centers
- Align Bottom

Available distribution operations include:

- Distribute Horizontal Spacing
- Distribute Vertical Spacing

Alignment requires at least two independent crop frames.

Spacing distribution requires at least three independent crop frames.

Grouped frames and mosaic areas are managed separately from these operations.

### Crop-Frame Groups

- Group multiple crop frames together
- Edit individual crop frames inside a group
- Ungroup grouped crop frames
- Preserve group information across page changes
- Preserve group information in project files
- Export grouped crop frames as a single combined image

### Aspect Ratios

- Set an aspect-ratio mode for each crop frame
- Use free resizing
- Preserve the current frame ratio
- Choose from 16:9, 9:16, 4:3, 3:2, and 1:1 presets
- Hold Shift while resizing to temporarily preserve the frame's current ratio
- Preserve per-frame aspect-ratio settings across page changes
- Preserve aspect-ratio settings through Undo and Redo
- Preserve aspect-ratio settings in project files
- Preserve aspect-ratio settings during export
- Use compact resize handles with a reduced hit area for easier work with closely spaced crop frames

### Mosaic Areas

Mosaic areas provide a lightweight way to obscure personal information or other sensitive content before export.

- Create rectangular mosaic areas
- Create multiple mosaic areas on the same page
- Move and resize mosaic areas
- Delete mosaic areas
- Undo and redo mosaic-area editing operations
- Store mosaic areas separately for each page
- Preserve mosaic areas across page changes
- Save and restore mosaic areas in project files
- Preserve mosaic areas when pages are deleted and restored with Undo
- Preview mosaic effects before export
- Apply mosaics to exported JPEG files
- Apply mosaics correctly to normal, rotated, and grouped crop frames

Mosaic areas are managed independently from crop frames.

They are therefore **not copied or pasted together with crop-frame layouts**. This helps prevent the same obscuring area from being unintentionally applied to unrelated images.

### Preview and Navigation

- Preview cropped photographs fitted to the available preview-pane width
- Preview mosaic effects in crop previews
- Click a crop preview to open a larger viewer
- Navigate between enlarged crop previews with Previous and Next controls
- Use the Left and Right arrow keys to navigate between enlarged crop previews
- Zoom and pan inside the enlarged crop-preview viewer
- Pan the main canvas with the middle mouse button
- Pan the main canvas with Space + left drag
- Display the selected crop frame with an animated border

### Export

- Configure output DPI
- Configure crop margins in millimeters
- Configure JPEG quality
- Export all crop frames from one selected page as JPEG files
- Show both percentage and processed/total crop counts during export
- Preserve original page numbers in exported filenames
- Preserve crop frames after export
- Confirm before overwriting existing files
- Export rotated crop frames
- Export grouped crop frames
- Apply mosaic processing during export

## Project Files

AlbumCrop Studio can save the current work as a project file.

A saved project can contain information such as:

- Loaded pages
- Crop-frame positions
- Crop-frame sizes
- Rotation angles
- Per-frame aspect-ratio modes
- Crop-frame group information
- Mosaic-area positions and sizes
- Page export selections
- Output settings

Aspect-ratio modes are stored separately for each crop frame.

Projects created before aspect-ratio or mosaic information was added remain compatible. Frames without saved ratio information are opened in free-resize mode, and older projects without mosaic information are opened without mosaic areas.

AlbumCrop Studio also checks the project-format version when opening a project.

Projects using a newer unsupported format are not opened. This helps prevent newer project data from being unintentionally lost by an older version of AlbumCrop Studio.

Project files are written using a temporary file before replacing the previous saved file. This reduces the risk of damaging an existing project if saving is interrupted.

AlbumCrop Studio Free can open projects containing up to 5 pages.

Projects containing more than 5 pages are not opened in the Free edition in order to avoid unintentionally loading or overwriting only part of a larger project.

Keep the original image and PDF files available in their original locations when reopening a project.

## Auto Save and Crash Recovery

AlbumCrop Studio can automatically save recovery data while a project contains unsaved changes.

Auto Save is intended as a recovery mechanism rather than a replacement for normal project saving.

Recovery data may be created when:

- A project contains unsaved changes
- At least one image or PDF page is loaded
- Automatic photo detection is not running
- Export is not running
- A multi-page paste operation is not running

If AlbumCrop Studio closes normally, the temporary recovery data is removed.

If the application or computer stops unexpectedly, the recovery data can remain available for the next startup.

When recovery data from a previous session is found, AlbumCrop Studio can offer the following choices:

- Recover
- Discard
- Cancel

Recovered work is opened as unsaved work so that the user can choose where to save it.

If source images required by the recovery data are missing, recovery is stopped and the recovery data is kept. The source images can then be restored to their original locations before trying again.

Invalid recovery files are skipped without preventing older valid recovery data from being found.

## Languages

AlbumCrop Studio currently supports the following interface languages:

- 日本語
- English
- 繁體中文

The interface language can be changed from Settings.

A restart is required after changing the language.

The Japanese interface is the source language used by the application. English and Traditional Chinese are provided through Qt translation files.

## Quick Start

A lightweight Quick Start guide is available from:

**Help → Quick Start**

The guide explains the basic workflow:

1. Open an image or PDF
2. Create crop frames using automatic detection or manual placement
3. Review and adjust crop frames
4. Check the preview and export the cropped images
5. Save the work as a project when needed

The initial empty canvas also provides basic guidance for loading an image or PDF and beginning the crop-frame workflow.

Quick Start is available on demand and is not shown automatically at application startup.

## Supported Platforms

### Officially Supported

- Windows 10
- Windows 11

AlbumCrop Studio Free is primarily developed and tested on Windows 11.

### Planned

- macOS

macOS support is planned, but it has not yet received the same level of testing as the Windows version.

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
3. Adjust the position, size, and rotation of each crop frame.
4. Choose free resizing, preserve the frame's current ratio, or select a preset aspect ratio for each frame.
5. Hold Shift while resizing when you want to temporarily preserve the frame's current ratio.
6. Use Ctrl-click to select multiple crop frames, or Ctrl+A to select all crop frames on the current page.
7. Use alignment or spacing-distribution operations when multiple independent crop frames should be arranged consistently.
8. Use Ctrl+C to copy or Ctrl+X to cut selected crop frames, then Ctrl+V to paste them while preserving their relative layout.
9. Copy or move crop-frame layouts to another page when needed.
10. Use multi-page paste when the same crop-frame layout should be applied to selected pages or all other loaded pages.
11. Group related crop frames when several separate crop areas should be treated as one output.
12. Use Group Frame Edit mode when individual frames inside a group need to be adjusted.
13. Create mosaic areas over content that should be obscured.
14. Adjust mosaic-area position and size independently from crop frames.
15. Switch the page list between thumbnail and compact modes when working with multiple pages.
16. Check cropped results in the preview pane.
17. Click a crop preview when you need a larger zoomable view or a clearer view of mosaic processing.
18. Navigate between enlarged previews with the Previous and Next controls or the Left and Right arrow keys.
19. Check one page in the page list as the export target.
20. Configure DPI, margin, and JPEG quality from the main window or Settings.
21. Choose an output folder.
22. Export all crop frames from the selected page.
23. To export another page, select that page as the export target and run export again.
24. Save the project when the crop-frame layout or other work should be reused later.

## Crop-Frame Groups

Multiple crop frames can be grouped together when several separate areas should be exported as a single combined image.

Grouped crop frames can still be edited individually by using **Group Frame Edit** mode.

Groups can also be removed when the frames should return to independent operation.

Group information is preserved across page changes, project saving and loading, and export.

## Mosaic Areas

Mosaic areas are intended as a lightweight archival support feature for obscuring areas such as personal information or other content that should not appear in exported images.

Mosaic areas:

- Are rectangular
- Can be created multiple times on the same page
- Can be moved and resized
- Can be deleted
- Support Undo and Redo
- Are stored separately for each page
- Are preserved in project files
- Are reflected in crop previews
- Are applied to exported JPEG files
- Work with normal, rotated, and grouped crop frames

Mosaic areas are managed independently from crop frames.

They are therefore **not copied or pasted together with crop-frame layouts**. This helps avoid unintentionally applying the same obscuring area to large numbers of unrelated images.

The main canvas displays mosaic areas as editable overlay frames. The crop preview and enlarged preview show the actual mosaic effect that will be applied during export.

## Important Notes

Before processing important or irreplaceable archival material:

- Keep the original files unchanged
- Create backups
- Save important work as an AlbumCrop Studio project
- Test the output with sample files
- Check exported photographs manually when accuracy is important
- Confirm that mosaic masking covers the intended area before publishing or sharing exported images

Automatic detection may require manual adjustment depending on the album layout, image quality, background, shadows, decorations, or damaged pages.

Auto Save and Crash Recovery are safety features, but they should not be treated as a substitute for regular project saving and external backups.

Mosaic masking is a visual processing aid and should not be treated as a substitute for legal, ethical, privacy, or archival review where such review is required.

## Known Limitations

- The Free edition can load up to 5 pages at one time
- The Free edition exports one selected page at a time
- Automatic detection may not identify every photograph correctly
- Overlapping photographs may require manual frame creation
- Decorative borders and page backgrounds may affect detection
- Mosaic areas are rectangular only
- Mosaic strength is currently fixed
- Mosaic areas are page-specific and are not included in crop-frame copy and paste operations
- Very large images and PDFs may require significant memory
- Only a limited number of recently viewed pages are cached in memory
- macOS has not yet received the same level of testing as Windows 11
- Advanced metadata and geolocation features are not included in AlbumCrop Studio Free

## Development Philosophy

AlbumCrop Studio aims to support more than image extraction.

The long-term goal is to help build accessible digital archives that can support historical research, international collaboration, and dialogue around photographic records.

The application is designed around reducing the time and manual effort required to prepare photographic materials while preserving a workflow that remains understandable, controllable, reproducible, and suitable for archival work.

The guiding idea of AlbumCrop Studio is:

**From Records to Resources, and from Resources to Assets.**

Future development may include tools for organizing contextual information, recording uncertain location evidence, and working with additional media formats.

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