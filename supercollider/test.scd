(
s.waitForBoot;

t = TempoClock(1);

OSCdef(\ping, {
	|msg, time, addr, recvPort|
	var request_id = msg[1];
	addr.sendMsg("/ping", request_id, "success");
}, '/ping');
)

