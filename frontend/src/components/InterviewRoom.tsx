'use client';

import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useAudio } from '../hooks/useAudio';
import { useWebSocket } from '../hooks/useWebSocket';
import VoiceVisualizer from './VoiceVisualizer';

const InterviewRoom: React.FC = () => {
  const [isMicMuted, setIsMicMuted] = useState(false);
  const [isSpeakerMuted, setIsSpeakerMuted] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [micActive, setMicActive] = useState(false);
  
  const { startMic, stopMic, playChunk, stopAllAudio } = useAudio();
  
  const isMicMutedRef = useRef(isMicMuted);
  const isSpeakerMutedRef = useRef(isSpeakerMuted);
  const isConnectedRef = useRef(false);
  const sendAudioRef = useRef<((data: string) => void) | null>(null);
  
  useEffect(() => {
    isMicMutedRef.current = isMicMuted;
  }, [isMicMuted]);
  
  useEffect(() => {
    isSpeakerMutedRef.current = isSpeakerMuted;
  }, [isSpeakerMuted]);
  
  // Use 127.0.0.1 to avoid localhost resolution issues in some environments
  const wsUrl = 'ws://127.0.0.1:8000/ws/interview';

  const wsOptions = React.useMemo(() => ({
    onAudioChunk: (base64: string) => {
      if (!isSpeakerMutedRef.current) {
        playChunk(base64);
      }
    },
    onInterrupted: () => {
      console.log('Interrupted! Stopping audio playback.');
      stopAllAudio();
    },
    onOpen: () => {
      console.log('WebSocket connected');
      isConnectedRef.current = true;
      setIsConnecting(false);
      setMicActive(true);
      startMic((base64) => {
        if (!isMicMutedRef.current && isConnectedRef.current && sendAudioRef.current) {
          sendAudioRef.current(base64);
        }
      });
    },
    onClose: () => {
      console.log('WebSocket disconnected');
      isConnectedRef.current = false;
      setIsConnecting(false);
      setMicActive(false);
      stopMic();
      stopAllAudio();
    },
    onError: (err: any) => {
      console.error('WebSocket Error:', err);
      isConnectedRef.current = false;
      setIsConnecting(false);
      setMicActive(false);
    }
  }), [playChunk, stopAllAudio, stopMic, startMic]);

  const { connect, disconnect, isConnected, sendAudio } = useWebSocket(wsUrl, wsOptions);
  
  useEffect(() => {
    sendAudioRef.current = sendAudio;
  }, [sendAudio]);

  const handleToggleConnection = useCallback(() => {
    if (isConnected) {
      disconnect();
      setMicActive(false);
    } else {
      console.log('Initiating connection...');
      setIsConnecting(true);
      connect();
    }
  }, [isConnected, disconnect, connect]);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-slate-900 text-white p-8">
      <div className="w-full max-w-2xl bg-slate-800 rounded-3xl p-12 shadow-2xl border border-slate-700 flex flex-col items-center gap-12">
        <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
          Project Raven
        </h1>
        
        <div className="relative w-64 h-64 flex items-center justify-center">
          <VoiceVisualizer isActive={micActive} isMuted={isMicMuted} />
          <div className={`absolute inset-0 rounded-full border-4 border-blue-500/20 animate-ping ${!micActive ? 'hidden' : ''}`} />
        </div>

        <div className="flex flex-wrap justify-center gap-6">
          <button
            onClick={handleToggleConnection}
            disabled={isConnecting}
            className={`px-8 py-4 rounded-full font-semibold transition-all shadow-lg active:scale-95 ${
              isConnecting 
                ? 'bg-black cursor-not-allowed opacity-90 ring-2 ring-blue-500 shadow-inner'
                : isConnected 
                  ? 'bg-red-600 hover:bg-red-700' 
                  : 'bg-blue-600 hover:bg-blue-700'
            }`}
          >
            {isConnecting ? 'Connecting...' : isConnected ? 'End Interview' : 'Start Interview'}
          </button>

          {isConnected && (
            <>
              <button
                onClick={() => setIsMicMuted(!isMicMuted)}
                className={`p-4 rounded-full transition-all border ${
                  isMicMuted 
                    ? 'bg-slate-700 border-red-500 text-red-500' 
                    : 'bg-slate-700 border-slate-600 text-slate-300 hover:border-blue-400'
                }`}
              >
                {isMicMuted ? 'Mic Muted' : 'Mic Active'}
              </button>

              <button
                onClick={() => setIsSpeakerMuted(!isSpeakerMuted)}
                className={`p-4 rounded-full transition-all border ${
                  isSpeakerMuted 
                    ? 'bg-slate-700 border-red-500 text-red-500' 
                    : 'bg-slate-700 border-slate-600 text-slate-300 hover:border-blue-400'
                }`}
              >
                {isSpeakerMuted ? 'AI Silent' : 'AI Speaking'}
              </button>
            </>
          )}
        </div>
        
        <p className="text-slate-400 text-sm italic">
          {isConnected ? 'Interview in progress. Speak naturally.' : 'Ready to begin your interview?'}
        </p>
      </div>
    </div>
  );
};

export default InterviewRoom;
