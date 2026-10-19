# Record the README demo: vhs docs/demo.tape
# Needs Ollama running with the default models.

Output docs/demo.gif
Require ollama

Set Shell zsh
Set FontSize 15
Set Width 1300
Set Height 760
Set Padding 20
Set Theme "Catppuccin Mocha"
Set TypingSpeed 45ms

Hide
Type `export TIDY_HOME=$(mktemp -d) PROJ=$PWD; rm -rf /tmp/tidy-demo && mkdir -p /tmp/tidy-demo && uv run --project $PROJ python $PROJ/scripts/make_fixtures.py /tmp/tidy-demo/Downloads >/dev/null && cd /tmp/tidy-demo/Downloads && alias tidy="uv run --quiet --project $PROJ tidy" && PS1="%F{cyan}~/Downloads%f ❯ " && clear`
Enter
Sleep 2s
Show

Type "ls"
Enter
Sleep 2.5s

Type "tidy plan ."
Enter
Wait+Screen@90s /Apply with/
Sleep 5s

Type "tidy apply last -y"
Enter
Sleep 2s
Type "clear && find . -type f -not -name .DS_Store | sort"
Enter
Sleep 5s

Type "tidy undo last && ls"
Enter
Sleep 4s
