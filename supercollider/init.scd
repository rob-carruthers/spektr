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

  OSCdef(\setBeatsPerSecond, {
    |msg, time, addr, recvPort|
    var requestId = msg[1];
    var newBeatsPerSecond = msg[2];

    ~clock.tempo = newBeatsPerSecond;
    addr.sendMsg("/set/beats_per_second", requestId, "ok", newBeatsPerSecond);
  }, "/set/beats_per_second");

  OSCdef(\setBeatsPerBar, {
    |msg, time, addr, recvPort|
    var requestId = msg[1];
    var newBeatsPerBar = msg[2];
    var atBeats = msg[3];

    if(atBeats > ~clock.beats, {
      ~clock.schedAbs(atBeats, {
        ~clock.beatsPerBar_(newBeatsPerBar);
        nil
      });
      addr.sendMsg("/set/beats_per_bar", requestId, "ok", newBeatsPerBar);
    }, {
      addr.sendMsg("/set/beats_per_bar", requestId, "late", ~clock.beats);
    });
  }, "/set/beats_per_bar");

)
