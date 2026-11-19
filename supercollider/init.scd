(
  ~clock = TempoClock.default;

  s.waitForBoot {
    SynthDef(\legato1, {
      arg freq = 440.0, amp = 0.2, gate = 1;
      var osc = SinOsc.ar(freq: freq, mul: amp);
      var env = EnvGen.kr(Env.adsr, gate, doneAction: Done.freeSelf);
      var snd = osc * env;
      Out.ar(0, [snd, snd]);
    }).add;
    s.sync;
  };

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

  ~dispatch = { |kind, id, args|
    // dispatch an event, its ID and args
    
    switch(kind,
      \note_on,  { s.sendMsg("/s_new", args[0], id, 0, 1, *args.drop(1)) },
      \note_set,  { s.sendMsg("/n_set", id, *args) },
      \note_off, { s.sendMsg("/n_set", id, \gate, 0) },
      { "unknown event kind: %".format(kind).warn }
    );
  };

  ~parseEvents = { |msg, start|
    var i = start;
    var events = List.new;
    var ok = true;

    while { ok and: { i < msg.size } } {
      var beats, kind, nArgs;

      // Walk through the message with a cursor, parsing out events/params as we go
      if(i + 3 > msg.size) { ok = false } {
        beats = msg[i];
        kind = msg[i + 1].asSymbol;
        nArgs = msg[i + 2].asInteger;
        if(i + 3 + nArgs > msg.size) { ok = false } {
          events.add((beats: beats, kind: kind,
            args: Array.fill(nArgs, { |k| msg[i + 3 + k] })));
          i = i + 3 + nArgs;
        };
      };
    };
    if(ok) { events.asArray } { nil }
  };

  OSCdef(\events, { |msg, time, addr|
    var requestId = msg[1];
    var nEvents = msg[2];
    var events = ~parseEvents.(msg, 3);
    var refs = Dictionary.new;

    // Walk through events, dispatching each one
    if(events.isNil or: { events.size != nEvents }, {
      addr.sendMsg("/events", requestId, "error", "malformed event stream");
    }, {
      events.do { |ev|
        var ref = ev[\args][0];
        var id;
        if(refs[ref].isNil) { refs[ref] = s.nextNodeID };
        id = refs[ref];
        ~clock.schedAbs(ev[\beats], {
          s.bind { ~dispatch.(ev[\kind], id, ev[\args].drop(1)) };
          nil
        });
      };
      addr.sendMsg("/events", requestId, "ok", events.size);
    });
  }, "/events");
)

