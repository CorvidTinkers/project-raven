import { useRef, useCallback } from 'react';

export const useAudio = () => {
  const audioContext = useRef<AudioContext | null>(null);
  const nextPlayTime = useRef(0);
  const sourceNodes = useRef<AudioBufferSourceNode[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);

  const initAudio = useCallback(async () => {
    if (!audioContext.current) {
      // Initialize context at 16kHz for input capture
      audioContext.current = new (window.AudioContext || (window as any).webkitAudioContext)({
        sampleRate: 16000,
      });
    }
    if (audioContext.current.state === 'suspended') {
      await audioContext.current.resume();
    }
  }, []);

  const startMic = useCallback(async (onAudioData: (base64Data: string) => void) => {
    await initAudio();
    
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    streamRef.current = stream;
    
    const source = audioContext.current!.createMediaStreamSource(stream);
    const processor = audioContext.current!.createScriptProcessor(4096, 1, 1);
    processorRef.current = processor;

    processor.onaudioprocess = (e) => {
      const inputData = e.inputBuffer.getChannelData(0);
      
      // Convert Float32 to Int16
      const pcm16 = new Int16Array(inputData.length);
      for (let i = 0; i < inputData.length; i++) {
        pcm16[i] = Math.max(-1, Math.min(1, inputData[i])) * 0x7FFF;
      }
      
      // Convert to Base64 safely
      const base64Data = btoa(
        new Uint8Array(pcm16.buffer).reduce((data, byte) => data + String.fromCharCode(byte), '')
      );
      onAudioData(base64Data);
    };

    source.connect(processor);
    processor.connect(audioContext.current!.destination);
  }, [initAudio]);

  const stopMic = useCallback(() => {
    streamRef.current?.getTracks().forEach(track => track.stop());
    processorRef.current?.disconnect();
    streamRef.current = null;
    processorRef.current = null;
  }, []);

  const playChunk = useCallback((base64Audio: string) => {
    if (!audioContext.current) return;

    // Decode base64 to ArrayBuffer
    const binaryString = atob(base64Audio);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    
    // Convert Int16 PCM to Float32 for playback
    const int16Array = new Int16Array(bytes.buffer);
    const float32Array = new Float32Array(int16Array.length);
    for (let i = 0; i < int16Array.length; i++) {
      float32Array[i] = int16Array[i] / 32768.0;
    }

    // Create a 24kHz buffer as per Gemini's output
    const buffer = audioContext.current.createBuffer(1, float32Array.length, 24000);
    buffer.getChannelData(0).set(float32Array);

    const source = audioContext.current.createBufferSource();
    source.buffer = buffer;
    source.connect(audioContext.current.destination);
    
    // Schedule playback to ensure gapless audio
    const currentTime = audioContext.current.currentTime;
    if (nextPlayTime.current < currentTime) {
      nextPlayTime.current = currentTime;
    }
    
    source.start(nextPlayTime.current);
    nextPlayTime.current += buffer.duration;
    sourceNodes.current.push(source);

    // Clean up finished nodes
    source.onended = () => {
      sourceNodes.current = sourceNodes.current.filter(n => n !== source);
    };
  }, []);

  const stopAllAudio = useCallback(() => {
    // BARGE-IN: Immediately kill all playing and scheduled audio
    sourceNodes.current.forEach(node => {
      try { node.stop(); } catch (e) {}
    });
    sourceNodes.current = [];
    nextPlayTime.current = 0;
  }, []);

  return { startMic, stopMic, playChunk, stopAllAudio };
};
