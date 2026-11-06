// AudioWorklet that downsamples to PCM16 mono @ 16 kHz for the STT relay.
const TARGET_RATE = 16000;

class DownsamplerProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._ratio = sampleRate / TARGET_RATE;
    this._buffer = new Float32Array(0);
    this._pos = 0;
  }

  process(inputs) {
    const input = inputs[0] && inputs[0][0];
    if (!input) return true;

    // Append new samples to our rolling buffer.
    const combined = new Float32Array(this._buffer.length + input.length);
    combined.set(this._buffer, 0);
    combined.set(input, this._buffer.length);
    this._buffer = combined;

    // How many target samples can we produce from what we have?
    const available = Math.floor(this._buffer.length / this._ratio);
    if (available < 1) return true;

    const out = new Int16Array(available);
    for (let i = 0; i < available; i++) {
      const idx = Math.floor(i * this._ratio + this._ratio / 2);
      let s = this._buffer[idx] || 0;
      s = Math.max(-1, Math.min(1, s));
      out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    // Keep the unconsumed tail for the next call.
    const consumed = Math.floor(available * this._ratio);
    this._buffer = this._buffer.slice(consumed);

    this.port.postMessage(out.buffer);
    return true;
  }
}

try {
  registerProcessor("downsampler-processor", DownsamplerProcessor);
} catch (e) {
  // Already registered or unsupported.
}
