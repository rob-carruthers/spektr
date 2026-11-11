(
s.waitForBoot;

t = TempoClock(1);

OSCdef(\ping, {
	|msg, time, addr, recvPort|
	var request_id = msg[1];
	addr.sendMsg("/ping", request_id, "success");
}, '/ping');

OSCdef(\state, {
	|msg, time, addr, recvPort|
	var request_id = msg[1];
	var barStartBeats = t.beats - t.beatInBar;
	addr.sendMsg("/state", request_id, t.bar, t.beats, t.tempo, t.beatsPerBar, barStartBeats);
}, '/state');
)

