(
s.waitForBoot;

t = TempoClock(1);

OSCdef(\ping, {
	|msg, time, addr, recvPort|
	addr.sendMsg("/ping", "success");
}, '/ping');
)

