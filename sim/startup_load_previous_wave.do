set WAVE_FILE $env(WAVE_FILE)
cp $WAVE_FILE.bk1.do $WAVE_FILE.do
set code [catch {
				view wave
				do $WAVE_FILE.do
				wave zoom full
} result]
