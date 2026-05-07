'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

const INPUT_SAMPLE_RATE = 16000;   // Gemini expects 16kHz input
const OUTPUT_SAMPLE_RATE = 24000;  // Gemini outputs 24kHz
const INPUT_BUFFER_SIZE = 1600;    // ~100ms chunks
const SCRIPT_PROCESSOR_BUFFER = 4096;
const ECHO_GUARD_RMS_THRESHOLD = 0.03;

export type VoiceStatus =
  | 'idle'
  | 'connecting'
  | 'connected'
  | 'listening'
  | 'speaking'
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
  sendUIReady: (view: string) => void;
  sendCode: (code: string) => void;
  onUIEvent?: (view: string) => void;
  onInterrupted?: () => void;
}

export function useVoiceWebSocket(options: {
  onUIEvent?: (view: string) => void;
  onInterrupted?: () => void;
} = {}): UseVoiceWebSocketReturn {
  const [status, setStatus] = useState<VoiceStatus>('idle');
  const [inputAmplitude, setInputAmplitude] = useState(0);
  const [outputAmplitude, setOutputAmplitude] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isMuted, setIsMuted] = useState(false);
  
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
  const activeOutputSourcesRef = useRef<Set<AudioBufferSourceNode>>(new Set());

  const optionsRef = useRef(options);
  useEffect(() => { optionsRef.current = options; }, [options]);

  const stopScheduledPlayback = useCallback((setListening: boolean) => {
    for (const source of activeOutputSourcesRef.current) {
      try {
        source.onended = null;
        source.stop();
      } catch {}
      source.disconnect();
    }
    activeOutputSourcesRef.current.clear();
    const outCtx = outputCtxRef.current;
    nextPlayTimeRef.current = outCtx ? outCtx.currentTime : 0;
    setOutputAmplitude(0);
    if (setListening) setStatus('listening');
  }, []);

  const cleanup = useCallback(() => {
    if (connectionTimerRef.current) {
      clearTimeout(connectionTimerRef.current);
      connectionTimerRef.current = null;
    }
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (sourceNodeRef.current) {
      sourceNodeRef.current.disconnect();
      sourceNodeRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(t => t.stop());
      mediaStreamRef.current = null;
    }
    if (inputCtxRef.current) {
      inputCtxRef.current.close().catch(() => {});
      inputCtxRef.current = null;
    }
    stopScheduledPlayback(false);
    if (outputCtxRef.current) {
      outputCtxRef.current.close().catch(() => {});
      outputCtxRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    nextPlayTimeRef.current = 0;
    pcmBufIdxRef.current = 0;
  }, [stopScheduledPlayback]);

  const float32ToInt16Buffer = (f32: Float32Array): ArrayBuffer => {
    const buf = new Int16Array(f32.length);
    for (let i = 0; i < f32.length; i++) {
      const clamped = Math.max(-1, Math.min(1, f32[i]));
      buf[i] = clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff;
    }
    return buf.buffer;
  };

  const scheduleAudioChunk = useCallback((int16Buffer: ArrayBuffer) => {
    const ctx = outputCtxRef.current;
    if (!ctx) return;

    const int16 = new Int16Array(int16Buffer);
    const float32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) float32[i] = int16[i] / 32768;

    let sum = 0;
    for (let i = 0; i < float32.length; i++) sum += float32[i] * float32[i];
    const rms = Math.sqrt(sum / float32.length);
    setOutputAmplitude(Math.min(1, rms * 4));

    const audioBuf = ctx.createBuffer(1, float32.length, OUTPUT_SAMPLE_RATE);
    audioBuf.copyToChannel(float32, 0);

    const source = ctx.createBufferSource();
    source.buffer = audioBuf;
    source.connect(ctx.destination);
    activeOutputSourcesRef.current.add(source);

    const now = ctx.currentTime;
    const startTime = Math.max(now, nextPlayTimeRef.current);
    source.start(startTime);
    nextPlayTimeRef.current = startTime + audioBuf.duration;

    setStatus('speaking');
    source.onended = () => {
      activeOutputSourcesRef.current.delete(source);
      if (activeOutputSourcesRef.current.size === 0 && nextPlayTimeRef.current <= ctx.currentTime + 0.05) {
        setStatus('listening');
        setOutputAmplitude(0);
      }
    };
  }, []);

  const connect = useCallback((candidateId: string) => {
    if (wsRef.current || connectionTimerRef.current) return;

    setStatus('connecting');
    setErrorMessage(null);

    connectionTimerRef.current = setTimeout(() => {
      connectionTimerRef.current = null;
      const wsBase = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
      const ws = new WebSocket(`${wsBase}/ws/interview?candidate_id=${candidateId}`);
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
            },
          });
          mediaStreamRef.current = stream;

          const inputCtx = new AudioContext({ sampleRate: INPUT_SAMPLE_RATE });
          inputCtxRef.current = inputCtx;
          const outputCtx = new AudioContext({ sampleRate: OUTPUT_SAMPLE_RATE });
          outputCtxRef.current = outputCtx;
          nextPlayTimeRef.current = outputCtx.currentTime;

          const source = inputCtx.createMediaStreamSource(stream);
          sourceNodeRef.current = source;
          const processor = inputCtx.createScriptProcessor(SCRIPT_PROCESSOR_BUFFER, 1, 1);
          processorRef.current = processor;

          processor.onaudioprocess = (e) => {
            if (ws.readyState !== WebSocket.OPEN) return;
            const inputData = e.inputBuffer.getChannelData(0);
            let sum = 0;
            for (let i = 0; i < inputData.length; i++) sum += inputData[i] * inputData[i];
            const rms = Math.sqrt(sum / inputData.length);

            const outCtx = outputCtxRef.current;
            const outputActive = outCtx ? nextPlayTimeRef.current > outCtx.currentTime + 0.05 : false;
            const isLikelyEchoOnly = outputActive && rms < ECHO_GUARD_RMS_THRESHOLD;

            setInputAmplitude(isMutedRef.current || isLikelyEchoOnly ? 0 : Math.min(1, rms * 5));
            if (isMutedRef.current || isLikelyEchoOnly) return;

            let offset = 0;
            while (offset < inputData.length) {
              const remaining = INPUT_BUFFER_SIZE - pcmBufIdxRef.current;
              const toCopy = Math.min(remaining, inputData.length - offset);
              pcmBufRef.current.set(inputData.subarray(offset, offset + toCopy), pcmBufIdxRef.current);
              pcmBufIdxRef.current += toCopy;
              offset += toCopy;
              if (pcmBufIdxRef.current >= INPUT_BUFFER_SIZE) {
                ws.send(float32ToInt16Buffer(pcmBufRef.current));
                pcmBufIdxRef.current = 0;
              }
            }
          };

          source.connect(processor);
          processor.connect(inputCtx.destination);
        } catch (err) {
          console.error('[VoiceWS] Mic error:', err);
          setStatus('error');
          setErrorMessage('Microphone access denied.');
        }
      };

      ws.onmessage = (event) => {
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
              optionsRef.current.onUIEvent?.(msg.view);
              break;
            case 'interrupted':
              stopScheduledPlayback(true);
              optionsRef.current.onInterrupted?.();
              break;
            case 'error':
              setStatus('error');
              setErrorMessage(msg.message);
              cleanup();
              break;
            case 'ping':
              ws.send(JSON.stringify({ type: 'pong' }));
              break;
          }
        } catch {}
      };

      ws.onerror = () => {
        setStatus('error');
        setErrorMessage('Connection error.');
      };

      ws.onclose = (e) => {
        if (e.code !== 4409) setStatus('idle');
        cleanup();
      };
    }, 80);
  }, [cleanup, scheduleAudioChunk, stopScheduledPlayback]);

  const disconnect = useCallback(() => {
    cleanup();
    setStatus('idle');
  }, [cleanup]);

  const toggleMute = useCallback(() => {
    const next = !isMutedRef.current;
    isMutedRef.current = next;
    setIsMuted(next);
    if (next) setInputAmplitude(0);
  }, []);

  const sendUIReady = useCallback((node: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'ui_ready', node }));
    }
  }, []);

  const sendCode = useCallback((code: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'submit_code', code }));
    }
  }, []);

  useEffect(() => cleanup, [cleanup]);

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
