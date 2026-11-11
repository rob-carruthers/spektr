(
  s.waitForBoot;

  ~clock = TempoClock(1);

  OSCdef(\ping, {
    |msg, time, addr, recvPort|
    var request_id = msg[1];
    addr.sendMsg("/ping", request_id, "success");
  }, "/ping");

  OSCdef(\state, {
    |msg, time, addr, recvPort|
    var request_id = msg[1];
    var barStartBeats = ~clock.beats - ~clock.beatInBar;
    addr.sendMsg("/state", request_id, ~clock.bar, ~clock.beats, ~clock.tempo, ~clock.beatsPerBar, barStartBeats);
  }, "/state");
)

