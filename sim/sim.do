onerror {
		quit -f -code 1
}

if [file exists work] {vdel -lib work -all}
vlib work
vmap -c
vmap work work

do vlog.do
do vsim.do

# log all signals
# set WildcardFilter [lsearch -not -all -inline $WildcardFilter Memory]
# log -r /*

# onbreak resume
run -all
quit
