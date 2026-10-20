# Shared by cputemp.sh and gputemp.sh (sourced, not run), so the CPU and GPU temperatures
# are graded the same: prints a temperature in whole °C as waybar JSON, with a class for how
# hot it is. The colours for the classes are in waybar/style.css.
temp_json() {
    local t=$1 level
    if   (( t >= 85 )); then level=critical   # the 5900X throttles at 90
    elif (( t >= 75 )); then level=hot
    elif (( t >= 50 )); then level=warm
    else                     level=cool
    fi
    printf '{"text": "%s°C", "class": "%s"}\n' "$t" "$level"
}
