# Changelog

All notable changes to AlbumCrop Studio will be documented in this file.

The project is currently in beta, and the changelog records user-visible
features, improvements, and important fixes.

## [Unreleased]

### Added

- Added a separate aspect-ratio mode for each crop frame
- Added free-resize and current-ratio locking modes
- Added 16:9, 9:16, 4:3, 3:2, and 1:1 aspect-ratio presets
- Added aspect-ratio support for corner and edge resizing
- Added persistence of per-frame aspect-ratio modes across page changes
- Added project-file storage and restoration of aspect-ratio modes
- Added backward compatibility for projects without aspect-ratio information
- Added aspect-ratio preservation when pages are deleted and restored
- Added aspect-ratio state support for crop-frame copy, deletion, undo, and redo
- Added free-resize defaults for automatically detected and generated frames
- Added multiple crop-frame selection
- Added grouped movement and deletion of selected crop frames
- Added multiple crop-frame copy and paste while preserving relative layout
- Added copy and paste of crop-frame layouts between pages during the same
  application session
- Added thumbnail and compact display modes for the page list
- Added crop-preview fitting to the available preview-pane width

### Changed

- Reduced the visual size and hit area of crop-frame resize handles
- Improved crop-preview resizing when the preview pane width changes

### Fixed

- Fixed redo losing the crop frame's saved aspect-ratio mode
- Fixed missing initialization of the crop-frame aspect-ratio state
- Fixed aspect-ratio modes not being restored after export
- Fixed page-list delete controls being clipped by long filenames in compact
  display mode

## [0.10.0-beta.2]

### Added

- Added page-level export selection
- Added export-selection persistence in project files
- Added faster page switching with a recently viewed page cache
- Added Shift-based aspect-ratio preservation while resizing
- Added background processing for automatic photo detection
- Added progress feedback during detection and export
- Added resizable page-list, canvas, and preview panes
- Improved crop-frame controls near the edges of the canvas

### Changed

- Disabled unnecessary debug-image generation during photo detection
- Preserved crop frames and rotation angles after export
- Updated the README for the beta release

## [0.10.0-beta.1]

### Added

- Initial public beta release for Windows
- Image and PDF loading
- Automatic photograph detection
- Manual crop-frame creation and editing
- Crop-frame movement, resizing, copying, rotation, and deletion
- Undo and redo
- Multiple-page projects
- Project saving and loading
- DPI, crop-margin, and JPEG-quality settings
- Batch JPEG export
- Overwrite confirmation