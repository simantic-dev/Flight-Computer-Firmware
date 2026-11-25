Output media/flight-computer-demo.gif
Set Shell zsh
Set Theme "Catppuccin Mocha"
Set Width 1280
Set Height 740
Set FontSize 16
Set Padding 18
Set Framerate 10
Set PlaybackSpeed 4
Env PS1 "$ "
Hide
Type 'export PATH="$HOME/.local/bin:$PATH" && cd "$(git rev-parse --show-toplevel)" && clear' Enter
Show
Type "./demo" Enter
Wait+Line@900s /^\$$/
Sleep 40s
# The recorded GIF was then re-timed with ffmpeg (scrolling part sped up to about 18 s, 10 s hold kept): recording time varied 4x with machine load.
