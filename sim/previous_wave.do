set WAVE_FILE $env(WAVE_FILE)
set code [catch {
				view wave
				do $WAVE_FILE.do
				wave zoom full
} result]
