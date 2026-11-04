JetBrains Mono font cache

This folder is used by `scripts/install_jetbrains_mono.sh`.

Expected contents after download:
- `JetBrainsMono-Regular.ttf`
- `JetBrainsMono-Bold.ttf`
- other `JetBrainsMono-*.ttf` variants

The installer script will:
1. check whether `JetBrains Mono` is already installed
2. download the latest release into this folder if the font files are missing
3. copy the files into `~/.local/share/fonts/JetBrainsMono`
4. refresh the font cache with `fc-cache`
