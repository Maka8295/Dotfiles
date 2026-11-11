#!/bin/bash
# Nemo's double-click handler for archives (extract-here.desktop, the default for them in
# ~/.config/mimeapps.list). Unpacks next to the archive, into a new folder unless everything in
# it already sits under one folder; if the files are already there File Roller asks first.
#
# Formats that are zips or tarballs underneath (.docx, .epub, .3mf, .apk, ...) inherit this
# handler from their parent MIME type, so only the exact types below are extracted and the
# rest open in File Roller, as they would have anyway.

for file in "$@"; do
    type=$(gio info -a standard::content-type "$file" | sed -n 's/^ *standard::content-type: //p')
    case "$type" in
        application/zip | application/x-7z-compressed | application/vnd.rar | \
        application/x-tar | application/x-tarz | application/x-tzo | application/*-compressed-tar | \
        application/gzip | application/zstd | application/x-xz | application/x-bzip1 | \
        application/x-bzip2 | application/x-lz4 | application/x-lzma | application/x-lzip | \
        application/x-lzop | application/x-lrzip | application/x-brotli | application/x-compress)
            file-roller --extract-here "$file" &
            ;;
        *)
            file-roller "$file" &
            ;;
    esac
done
wait
