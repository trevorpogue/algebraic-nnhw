set WAVE_FILE $env(WAVE_FILE)
set code [catch {
                cp $WAVE_FILE.do $WAVE_FILE\.bk1\.do
} result]
set code [catch {
                cp $WAVE_FILE\.bk1\.do $WAVE_FILE\.bk2\.do
} result]
set code [catch {
                cp $WAVE_FILE\.bk2\.do $WAVE_FILE\.bk3\.do
} result]
set code [catch {
                cp $WAVE_FILE\.bk3\.do $WAVE_FILE\.bk4\.do
} result]
set code [catch {
                cp $WAVE_FILE\.bk4\.do $WAVE_FILE\.bk5\.do
} result]
set code [catch {
                cp $WAVE_FILE\.bk5\.do $WAVE_FILE\.bk6\.do
} result]
set code [catch {
                cp $WAVE_FILE\.bk6\.do $WAVE_FILE\.bk7\.do
} result]
write format wave -window .main_pane.wave.interior.cs.body.pw.wf $WAVE_FILE\.do
dataset restart
wave zoom full
