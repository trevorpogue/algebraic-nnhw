[ -d ~/mydata ] && source ~/mydata/.bashrc
export LIBPYTHON_LOC=$(cocotb-config --libpython)
export WAVE_FILE=wave
export LIBCOCOTB_LOC=$(cocotb-config --lib-name-path vpi questa)
export MODULE=tests
cd /home/v38218/mydata/nnhw/device/sim/top3
echo "starting vsim"
vsim -view vsim.wlf -do startup_load_previous_wave.do
echo "done vsim"
mv /home/v38218/mydata/nnhw/device/sim/top3/*outlog* /home/v38218/mydata/nnhw/
