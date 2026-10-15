# Terminal greeting: a random Old English phrase from ~/Dotfiles/fish/greetings.txt and its
# translation on one line, in red fraktur: ♰ phrase ♱ translation ♰. Never the same twice in a row.
function dungeon_greeting
    set -l file ~/Dotfiles/fish/greetings.txt
    test -r $file; or return
    set -l lines (string match -rv '^\s*(#|$)' < $file)
    test (count $lines) -gt 0; or return

    # pick one, avoiding the phrase shown last time
    set -l last_file ~/.cache/dungeon_greeting_last
    set -l last (cat $last_file 2>/dev/null)
    set -l pick (random 1 (count $lines))
    if test (count $lines) -gt 1; and test "$pick" = "$last"
        set pick (math "$pick % "(count $lines)" + 1")
    end
    mkdir -p ~/.cache; echo $pick > $last_file

    set -l parts (string split -m1 \t -- $lines[$pick])
    set -l phrase (__dungeon_fraktur --wynn $parts[1])
    set -l translation (__dungeon_fraktur $parts[2])

    # ♰ Old English ♱ translation ♰  (the middle cross is the prompt's ♱)
    set_color red
    echo "♰ $phrase ♱ $translation ♰"
    set_color normal
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
