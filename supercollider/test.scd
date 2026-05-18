(
s.boot;

t = TempoClock(1);

SynthDef(\blip, {
  arg freq=440, amp=0.1;

  var env = Env.perc(0.01, 0.2).kr(doneAction:2);
  var sig = SinOsc.ar(freq) * env * amp;

  Out.ar(0, sig ! 2);
}).add;


OSCdef(\notes, {
  |msg|
  var freq = msg[1];
  t.schedAbs(t.nextBar, {Synth(\blip, [\freq, freq])});
},
'/note');
)

