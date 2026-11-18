(
  s.waitForBoot;

  ~activeNotes = Dictionary.new;
  ~clock = TempoClock.default;

  SynthDef(\perc1, {
    arg freq = 440.0, amp = 0.2;
    var osc = SinOsc.ar(freq: freq, mul: amp);
    var env = Env.perc(releaseTime: 0.5).kr(doneAction: 2);
    var snd = osc * env;
    Out.ar(0, [snd, snd]);
  }).add;

  SynthDef(\legato1, {
    arg freq = 440.0, amp = 0.2, gate = 1;
    var osc = SinOsc.ar(freq: freq, mul: amp);
    var env = EnvGen.kr(Env.adsr, gate, doneAction: Done.freeSelf);
    var snd = osc * env;
    Out.ar(0, [snd, snd]);
  }).add;

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

  ~dispatch = { |eventType, params|

    switch(eventType,
      \note_on, {
        var id = params[0];
        var synthName = params[1].asSymbol;
        var freq = params[2];

        ~activeNotes[id] = Synth(synthName, [\freq, freq]);
      },
      \note_off, {
        var id = params[0];
        var synth = ~activeNotes.removeAt(id);
        if (synth.notNil) {
          synth.set(\gate, 0);
        };
      }
    );
  };

  OSCdef(\events, {
    |msg, time, addr, recvPort|
    var requestId = msg[1];
    var nEvents = msg[2];
    var handled = 0;
    
    // event stream starts at msg[3]
    var streamIdx = 3;

    while { streamIdx < msg.size } {
      var atBeats = msg[streamIdx];
      var eventType = msg[streamIdx + 1].asSymbol;
      var nParams = msg[streamIdx + 2].asInteger;
      var params;

      if (streamIdx + nParams > msg.size) {
        Error("Malformed event stream").throw;
      };

      streamIdx = streamIdx + 3;

      params = msg.copyRange(streamIdx, streamIdx + nParams - 1);
      streamIdx = streamIdx + nParams;
      ~clock.schedAbs(atBeats, {
        ~dispatch.value(eventType, params);
        nil;
      });
      handled = handled + 1;

    };
    addr.sendMsg("/events", requestId, "ok", handled);
  }, "/events");
)

