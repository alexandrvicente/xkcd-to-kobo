# xkcd-to-kobo

A Python script to download [xkcd](https://xkcd.com/) comics and generate a kepub file optimized for Kobo e-readers and a GitHub action using [rclone](https://rclone.org/) to sync to Dropbox or Google Drive for automatic delivery. Also compatible with other ePUB readers.

## How to use

### Manual downloads

[Download the latest release.](https://github.com/alexandrvicente/xkcd-to-kobo/releases/download/latest/xkcd.kepub.epub)

### Sync to Dropbox or Google Drive

1. Set up rclone locally with your cloud storage provider.
2. Clone this repository.
3. Add the following secrets to your GitHub repository:
   - `RCLONE_CONFIG`: Base64-encoded contents of your rclone.conf file.
   - `RCLONE_DESTINATION`: The destination path in your cloud storage provider.
