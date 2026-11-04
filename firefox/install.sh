#!/bin/bash
# Installs the dungeonOS theme into your Firefox profile.
#
#   ~/Dotfiles/firefox/install.sh            link chrome/ and user.js into the profile
#   ~/Dotfiles/firefox/install.sh --remove   take them out again
#
# The profile is the one Firefox starts with (the [Install...] Default= in profiles.ini).
# Anything already in the way is moved to <name>.bak-<date>. Restart Firefox afterwards:
# it only reads userChrome.css, userContent.css and user.js when it starts.

set -euo pipefail
HERE="$(cd "$(dirname "$(realpath "$0")")" && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"

# Firefox 147+ keeps profiles in ~/.config/mozilla/firefox, older ones in ~/.mozilla/firefox
profiles() {
    local root
    for root in "${XDG_CONFIG_HOME:-$HOME/.config}/mozilla/firefox" "$HOME/.mozilla/firefox"; do
        [ -f "$root/profiles.ini" ] || continue
        python3 - "$root" <<'PY'
import configparser, os, sys
root = sys.argv[1]
ini = configparser.ConfigParser(interpolation=None)
ini.read(os.path.join(root, "profiles.ini"))
def where(path, relative):
    return os.path.join(root, path) if relative != "0" else path
# the profile each Firefox install starts with
found = [ini[s]["Default"] for s in ini.sections() if s.startswith("Install") and "Default" in ini[s]]
paths = {ini[s]["Path"]: where(ini[s]["Path"], ini[s].get("IsRelative", "1"))
         for s in ini.sections() if s.startswith("Profile") and "Path" in ini[s]}
if not found:   # no [Install] section: the profile marked Default=1
    found = [ini[s]["Path"] for s in ini.sections()
             if s.startswith("Profile") and ini[s].get("Default") == "1"]
for path in dict.fromkeys(found):
    print(paths.get(path, where(path, "1")))
PY
    done
}

mapfile -t PROFILES < <(profiles)
if [ "${#PROFILES[@]}" = 0 ]; then
    echo "  No Firefox profile found; start Firefox once, close it, then rerun this."
    exit 0
fi

# link <source> <destination>, saving whatever was there
link() {
    local src="$1" dest="$2"
    if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$src" ]; then
        echo "  ok    $dest"
        return
    fi
    if [ -e "$dest" ] || [ -L "$dest" ]; then
        mv "$dest" "$dest.bak-$STAMP"
        echo "  saved old $dest -> $dest.bak-$STAMP"
    fi
    ln -sfn "$src" "$dest"
    echo "  link  $dest -> $src"
}

for profile in "${PROFILES[@]}"; do
    [ -d "$profile" ] || { echo "  skip  $profile (missing)"; continue; }
    if [ "${1:-}" = "--remove" ]; then
        for name in chrome user.js; do
            if [ -L "$profile/$name" ] && [[ "$(readlink "$profile/$name")" == "$HERE/"* ]]; then
                rm "$profile/$name"
                echo "  removed $profile/$name"
            fi
        done
        # user.js only adds prefs, so take the theme's back out of prefs.js as well
        # (Firefox rewrites prefs.js when it quits, so do this with Firefox closed)
        if [ -f "$profile/prefs.js" ]; then
            sed -i -E '/"(toolkit\.legacyUserProfileCustomizations\.stylesheets|browser\.display\.(background|foreground)_color\.dark|ui\.text(SelectAttention|Highlight)(Background|Foreground))"/d' "$profile/prefs.js"
        fi
    else
        link "$HERE/chrome" "$profile/chrome"
        link "$HERE/user.js" "$profile/user.js"
    fi
done

if pgrep -x firefox >/dev/null; then
    echo "  Firefox is running: restart it to see the change."
fi
