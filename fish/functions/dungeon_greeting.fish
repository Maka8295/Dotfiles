# Terminal greeting: a random Old English phrase from ~/Dotfiles/fish/greetings.txt and its
# translation on one line, in red fraktur: ♰ phrase ♱ translation ♰. Only phrases that fit
# the window's width are picked (in a very narrow window, just the phrase without its
# translation), and never the same one twice in a row.
function dungeon_greeting
    set -l file ~/Dotfiles/fish/greetings.txt
    test -r $file; or return
    set -l lines (string match -rv '^\s*(#|$)' < $file)
    test (count $lines) -gt 0; or return
    set -l cols $COLUMNS
    test -n "$cols"; or set cols 80

    # what fits: the whole greeting if possible, otherwise the phrase on its own. The fraktur
    # letters take one column each like the plain ones, so the plain text measures the same.
    set -l fits
    set -l short 0
    for line in $lines
        set -l parts (string split -m1 \t -- $line)
        test (string length -V -- "♰ $parts[1] ♱ $parts[2] ♰") -le $cols; and set -a fits $line
    end
    if test (count $fits) -eq 0
        set short 1
        for line in $lines
            set -l parts (string split -m1 \t -- $line)
            test (string length -V -- "♰ $parts[1] ♰") -le $cols; and set -a fits $line
        end
    end
    test (count $fits) -gt 0; or return

    # pick one, avoiding the phrase shown last time
    set -l last_file ~/.cache/dungeon_greeting_last
    set -l last (cat $last_file 2>/dev/null)
    if test (count $fits) -gt 1; and set -l i (contains -i -- "$last" $fits)
        set -e fits[$i]
    end
    set -l pick $fits[(random 1 (count $fits))]
    mkdir -p ~/.cache; printf '%s\n' $pick > $last_file

    set -l parts (string split -m1 \t -- $pick)
    set -l phrase (__dungeon_fraktur --wynn $parts[1])

    # ♰ Old English ♱ translation ♰  (the middle cross is the prompt's ♱)
    set_color red
    if test $short = 1
        echo "♰ $phrase ♰"
    else
        echo "♰ $phrase ♱ "(__dungeon_fraktur $parts[2])" ♰"
    end
    set_color normal
    echo   # a blank line before the first prompt, the same gap as between commands
end

# plain letters -> bold fraktur (long vowels keep their macron); --wynn also turns w into ƿ
function __dungeon_fraktur
    set -l wynn 0
    if test "$argv[1]" = --wynn
        set wynn 1
        set -e argv[1]
    end
    set -l from 'a' 'A' 'b' 'B' 'c' 'C' 'd' 'D' 'e' 'E' 'f' 'F' 'g' 'G' 'h' 'H' 'i' 'I' 'j' 'J' 'k' 'K' 'l' 'L' 'm' 'M' 'n' 'N' 'o' 'O' 'p' 'P' 'q' 'Q' 'r' 'R' 's' 'S' 't' 'T' 'u' 'U' 'v' 'V' 'w' 'W' 'x' 'X' 'y' 'Y' 'z' 'Z' 'ā' 'ē' 'ī' 'ō' 'ū' 'ȳ' 'Ā' 'Ē' 'Ī' 'Ō' 'Ū' 'Ȳ' 'ǣ' 'Ǣ'
    set -l to '𝖆' '𝕬' '𝖇' '𝕭' '𝖈' '𝕮' '𝖉' '𝕯' '𝖊' '𝕰' '𝖋' '𝕱' '𝖌' '𝕲' '𝖍' '𝕳' '𝖎' '𝕴' '𝖏' '𝕵' '𝖐' '𝕶' '𝖑' '𝕷' '𝖒' '𝕸' '𝖓' '𝕹' '𝖔' '𝕺' '𝖕' '𝕻' '𝖖' '𝕼' '𝖗' '𝕽' '𝖘' '𝕾' '𝖙' '𝕿' '𝖚' '𝖀' '𝖛' '𝖁' '𝖜' '𝖂' '𝖝' '𝖃' '𝖞' '𝖄' '𝖟' '𝖅' '𝖆̄' '𝖊̄' '𝖎̄' '𝖔̄' '𝖚̄' '𝖞̄' '𝕬̄' '𝕰̄' '𝕴̄' '𝕺̄' '𝖀̄' '𝖄̄' 'ǣ' 'Ǣ'
    set -l out
    for c in (string split '' -- "$argv")
        if test $wynn = 1; and contains -- $c w W
            test $c = w; and set c ƿ; or set c Ƿ
        else if set -l i (contains -i -- $c $from)
            set c $to[$i]
        end
        set -a out $c
    end
    string join '' -- $out
end
