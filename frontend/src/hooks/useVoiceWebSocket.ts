'use client';

/**
 * useVoiceWebSocket — Project Raven voice session hook.
 *
 * Audio pipeline:
 *   Mic → getUserMedia → ScriptProcessorNode → Float32→Int16 → WS binary send
 *   WS binary recv ← Int16 PCM 24kHz ← Gemini Live ← Backend
 *   Int16→Float32 → AudioBuffer scheduled on AudioContext (gapless playback)
 *
 * Steering protocol:
 *   - "connected"       → status: listening
 *   - "ui_event"        → onUIEvent(view) callback → React mounts component
 *   - "interrupted"     → flush output audio queue, status: listening
 *   - "code_received"   → onCodeReceived() callback
 *   - "error"           → status: error, cleanup
 *
 * ui_ready handshake:
 *   After onUIEvent fires and the component mounts, the parent calls
 *   sendUIReady(node) so the backend can release its asyncio.Event and
 *   soft-steer Gemini with the new stage instruction.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

const INPUT_SAMPLE_RATE  = 16000;   // Gemini Live expects 16kHz input
const OUTPUT_SAMPLE_RATE = 24000;   // Gemini Live outputs 24kHz
const INPUT_BUFFER_SIZE  = 1600;    // ~100ms of samples per send
const SCRIPT_PROCESSOR_BUFFER = 4096;
const ECHO_GUARD_RMS_THRESHOLD = 0.03; // Drop mic frames below this RMS during playback

export type VoiceStatus =
  | 'idle'
  | 'connecting'
  | 'connected'
  | 'listening'
  | 'speaking'
  | 'thinking'
  | 'finished'
  | 'error';

export interface UseVoiceWebSocketReturn {
  status: VoiceStatus;
  inputAmplitude: number;
  outputAmplitude: number;
  errorMessage: string | null;
  isMuted: boolean;
  connect: (candidateId: string) => void;
  disconnect: () => void;
  toggleMute: () => void;
  sendUIReady: (node: string) => void;
  sendCode: (code: string) => void;
}

interface Options {
  onUIEvent?: (view: string, stage: string) => void;
  onInterrupted?: () => void;
  onCodeReceived?: (stage: string) => void;
  onFinished?: () => void;
}

export function useVoiceWebSocket(options: Options = {}): UseVoiceWebSocketReturn {
  const [status, setStatus] = useState<VoiceStatus>('idle');
  const [inputAmplitude, setInputAmplitude] = useState(0);
  const [outputAmplitude, setOutputAmplitude] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isMuted, setIsMuted] = useState(false);

  // Stable refs — survive renders without recreating the WebSocket
  const isMutedRef = useRef(false);
  const wsRef = useRef<WebSocket | null>(null);
  const connectionTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inputCtxRef = useRef<AudioContext | null>(null);
  const outputCtxRef = useRef<AudioContext | null>(null);
  const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const pcmBufRef = useRef<Float32Array>(new Float32Array(INPUT_BUFFER_SIZE));
  const pcmBufIdxRef = useRef(0);
  const nextPlayTimeRef = useRef(0);
  const activeSourcesRef = useRef<Set<AudioBufferSourceNode>>(new Set());

  // Keep options callback refs stable
  const optionsRef = useRef(options);
  useEffect(() => { optionsRef.current = options; }, [options]);

  // ── Flush playback queue (barge-in) ────────────────────────────────────────
  const stopScheduledPlayback = useCallback((setListening: boolean) => {
    for (const source of activeSourcesRef.current) {
      try { source.onended = null; source.stop(); } catch { /* already stopped */ }
      source.disconnect();
    }
    activeSourcesRef.current.clear();
    const out = outputCtxRef.current;
    nextPlayTimeRef.current = out ? out.currentTime : 0;
    setOutputAmplitude(0);
    if (setListening) setStatus('listening');
  }, []);

  // ── Cleanup all resources ──────────────────────────────────────────────────
  const cleanup = useCallback(() => {
    // Cancel pending Strict Mode deferred connection
    if (connectionTimerRef.current !== null) {
      clearTimeout(connectionTimerRef.current);
      connectionTimerRef.current = null;
    }
    if (processorRef.current) { processorRef.current.disconnect(); processorRef.current = null; }
    if (sourceNodeRef.current) { sourceNodeRef.current.disconnect(); sourceNodeRef.current = null; }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(t => t.stop());
      mediaStreamRef.current = null;
    }
    if (inputCtxRef.current && inputCtxRef.current.state !== 'closed') {
      inputCtxRef.current.close().catch(() => {});
      inputCtxRef.current = null;
    }
    stopScheduledPlayback(false);
    if (outputCtxRef.current && outputCtxRef.current.state !== 'closed') {
      outputCtxRef.current.close().catch(() => {});
      outputCtxRef.current = null;
    }
    if (wsRef.current) {
      if (wsRef.current.readyState === WebSocket.OPEN) {
        // Graceful close — tell backend we're done
        try { wsRef.current.send(JSON.stringify({ type: 'end' })); } catch { /* ignore */ }
      }
      if (
        wsRef.current.readyState === WebSocket.OPEN ||
        wsRef.current.readyState === WebSocket.CONNECTING
      ) {
        wsRef.current.close();
      }
      wsRef.current = null;
    }
    nextPlayTimeRef.current = 0;
    pcmBufIdxRef.current = 0;
  }, [stopScheduledPlayback]);

  // ── PCM conversion ─────────────────────────────────────────────────────────
  const float32ToInt16 = (f32: Float32Array): ArrayBuffer => {
    const buf = new Int16Array(f32.length);
    for (let i = 0; i < f32.length; i++) {
      const c = Math.max(-1, Math.min(1, f32[i]));
      buf[i] = c < 0 ? c * 0x8000 : c * 0x7fff;
    }
    return buf.buffer;
  };

  // ── Schedule Gemini output audio ───────────────────────────────────────────
  const scheduleAudioChunk = useCallback((int16Buffer: ArrayBuffer) => {
    const ctx = outputCtxRef.current;
    if (!ctx) return;

    const int16 = new Int16Array(int16Buffer);
    const f32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) f32[i] = int16[i] / 32768;

    // Output amplitude for visualizer
    let sum = 0;
    for (let i = 0; i < f32.length; i++) sum += f32[i] * f32[i];
    setOutputAmplitude(Math.min(1, Math.sqrt(sum / f32.length) * 4));

    const audioBuf = ctx.createBuffer(1, f32.length, OUTPUT_SAMPLE_RATE);
    audioBuf.copyToChannel(f32, 0);

    const source = ctx.createBufferSource();
    source.buffer = audioBuf;
    source.connect(ctx.destination);
    activeSourcesRef.current.add(source);

    const now = ctx.currentTime;
    const startAt = Math.max(now, nextPlayTimeRef.current);
    source.start(startAt);
    nextPlayTimeRef.current = startAt + audioBuf.duration;

    setStatus('speaking');
    source.onended = () => {
      activeSourcesRef.current.delete(source);
      if (
        activeSourcesRef.current.size === 0 &&
        nextPlayTimeRef.current <= ctx.currentTime + 0.05
      ) {
        setStatus('listening');
        setOutputAmplitude(0);
      }
    };
  }, []);

  // ── Connect ────────────────────────────────────────────────────────────────
  const connect = useCallback((candidateId: string) => {
    if (wsRef.current || connectionTimerRef.current) return;
    setStatus('connecting');
    setErrorMessage(null);

    // 80ms delay absorbs React Strict Mode double-mount without creating ghost sockets
    connectionTimerRef.current = setTimeout(() => {
      connectionTimerRef.current = null;
      const wsBase = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
      const url = `${wsBase}/ws/interview?candidate_id=${candidateId}`;
      const ws = new WebSocket(url);
      wsRef.current = ws;
      ws.binaryType = 'arraybuffer';

      ws.onopen = async () => {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
              sampleRate: INPUT_SAMPLE_RATE,
              channelCount: 1,
              echoCancellation: true,
              noiseSuppression: true,
              autoGainControl: true,
            },
          });
          mediaStreamRef.current = stream;

          const inputCtx = new AudioContext({ sampleRate: INPUT_SAMPLE_RATE });
          const outputCtx = new AudioContext({ sampleRate: OUTPUT_SAMPLE_RATE });
          inputCtxRef.current = inputCtx;
          outputCtxRef.current = outputCtx;
          nextPlayTimeRef.current = outputCtx.currentTime;

          const source = inputCtx.createMediaStreamSource(stream);
          sourceNodeRef.current = source;

          const processor = inputCtx.createScriptProcessor(SCRIPT_PROCESSOR_BUFFER, 1, 1);
          processorRef.current = processor;

          processor.onaudioprocess = (e) => {
            if (ws.readyState !== WebSocket.OPEN) return;
            const inputData = e.inputBuffer.getChannelData(0);

            // RMS for input visualizer + echo guard
            let sum = 0;
            for (let i = 0; i < inputData.length; i++) sum += inputData[i] * inputData[i];
            const rms = Math.sqrt(sum / inputData.length);

            const outCtx = outputCtxRef.current;
            const outputActive = outCtx
              ? nextPlayTimeRef.current > outCtx.currentTime + 0.05
              : false;
            const isEchoOnly = outputActive && rms < ECHO_GUARD_RMS_THRESHOLD;

            setInputAmplitude(isMutedRef.current || isEchoOnly ? 0 : Math.min(1, rms * 5));
            if (isMutedRef.current || isEchoOnly) return;

            // Accumulate and send in fixed-size chunks
            let offset = 0;
            while (offset < inputData.length) {
              const remaining = INPUT_BUFFER_SIZE - pcmBufIdxRef.current;
              const toCopy = Math.min(remaining, inputData.length - offset);
              pcmBufRef.current.set(inputData.subarray(offset, offset + toCopy), pcmBufIdxRef.current);
              pcmBufIdxRef.current += toCopy;
              offset += toCopy;
              if (pcmBufIdxRef.current >= INPUT_BUFFER_SIZE) {
                ws.send(float32ToInt16(pcmBufRef.current));
                pcmBufIdxRef.current = 0;
              }
            }
          };

          source.connect(processor);
          processor.connect(inputCtx.destination);
        } catch (err) {
          console.error('[VoiceWS] Mic error:', err);
          setStatus('error');
          setErrorMessage('Microphone access denied. Allow microphone access and try again.');
        }
      };

      ws.onmessage = (event) => {
        // Binary: PCM audio from Gemini
        if (event.data instanceof ArrayBuffer) {
          scheduleAudioChunk(event.data);
          return;
        }

        try {
          const msg = JSON.parse(event.data as string);
          switch (msg.type) {
            case 'connected':
              setStatus('listening');
              break;

            case 'ui_event':
              optionsRef.current.onUIEvent?.(msg.view, msg.stage ?? '');
              break;

            case 'interrupted':
              stopScheduledPlayback(true);
              optionsRef.current.onInterrupted?.();
              break;

            case 'code_received':
              optionsRef.current.onCodeReceived?.(msg.stage ?? '');
              break;

            case 'finished':
              setStatus('finished');
              optionsRef.current.onFinished?.();
              cleanup();
              break;

            case 'error':
              setStatus('error');
              setErrorMessage(msg.message || 'Unknown error from server.');
              cleanup();
              break;

            case 'pong':
              break; // heartbeat ack — no-op
          }
        } catch { /* malformed JSON — ignore */ }
      };

      ws.onerror = () => {
        setStatus('error');
        setErrorMessage('WebSocket connection error. Check if the backend is running.');
      };

      ws.onclose = (e) => {
        if (e.code === 4409) return; // duplicate connection rejected — silently ignore
        if (status !== 'finished' && status !== 'error') setStatus('idle');
        cleanup();
      };
    }, 80);
  }, [cleanup, scheduleAudioChunk, status, stopScheduledPlayback]);

  // ── Disconnect ─────────────────────────────────────────────────────────────
  const disconnect = useCallback(() => {
    cleanup();
    setStatus('idle');
  }, [cleanup]);

  // ── Mute toggle ────────────────────────────────────────────────────────────
  const toggleMute = useCallback(() => {
    const next = !isMutedRef.current;
    isMutedRef.current = next;
    setIsMuted(next);
    if (next) setInputAmplitude(0);
  }, []);

  // ── ui_ready handshake ─────────────────────────────────────────────────────
  const sendUIReady = useCallback((node: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'ui_ready', node }));
    }
  }, []);

  // ── Code submission ────────────────────────────────────────────────────────
  const sendCode = useCallback((code: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'submit_code', code }));
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => () => { cleanup(); }, [cleanup]);

  return {
    status,
    inputAmplitude,
    outputAmplitude,
    errorMessage,
    isMuted,
    connect,
    disconnect,
    toggleMute,
    sendUIReady,
    sendCode,
  };
}
