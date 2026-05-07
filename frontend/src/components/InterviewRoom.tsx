'use client';

import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useAudio } from '../hooks/useAudio';
import { useWebSocket } from '../hooks/useWebSocket';
import VoiceVisualizer from './VoiceVisualizer';

const InterviewRoom: React.FC = () => {
  // State
  const [candidateId, setCandidateId] = useState<string | null>(null);
  const [isPreGenerating, setIsPreGenerating] = useState(false);
  const [currentView, setCurrentView] = useState('avatar'); // avatar, monaco, report
  
  const [isMicMuted, setIsMicMuted] = useState(false);
  const [isSpeakerMuted, setIsSpeakerMuted] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [micActive, setMicActive] = useState(false);
  
  const { startMic, stopMic, playChunk, stopAllAudio } = useAudio();
  
  const isMicMutedRef = useRef(isMicMuted);
  const isSpeakerMutedRef = useRef(isSpeakerMuted);
  const isConnectedRef = useRef(false);
  const sendAudioRef = useRef<((data: string) => void) | null>(null);
  const sendUIReadyRef = useRef<((node: string) => void) | null>(null);
  
  useEffect(() => {
    isMicMutedRef.current = isMicMuted;
  }, [isMicMuted]);
  
  useEffect(() => {
    isSpeakerMutedRef.current = isSpeakerMuted;
  }, [isSpeakerMuted]);
  
  // Dynamic WebSocket URL
  const wsUrl = candidateId 
    ? `ws://127.0.0.1:8000/ws/interview?candidate_id=${candidateId}` 
    : '';

  const wsOptions = React.useMemo(() => ({
    onAudioChunk: (base64: string) => {
      if (!isSpeakerMutedRef.current) {
        playChunk(base64);
      }
    },
    onInterrupted: () => {
      stopAllAudio();
    },
    onUIEvent: (view: string) => {
      setCurrentView(view);
      // Wait a moment for UI to mount, then signal ready
      setTimeout(() => {
        if (sendUIReadyRef.current) {
          sendUIReadyRef.current(view);
        }
      }, 500);
    },
    onOpen: () => {
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

  const { connect, disconnect, isConnected, sendAudio, sendUIReady } = useWebSocket(wsUrl, wsOptions);
  
  useEffect(() => {
    sendAudioRef.current = sendAudio;
    sendUIReadyRef.current = sendUIReady;
  }, [sendAudio, sendUIReady]);

  // Handle Resume Upload (Simplified for demo)
  const handleUpload = async () => {
    setIsPreGenerating(true);
    try {
      const formData = new FormData();
      formData.append('jd_text', 'Seeking a Senior Python Developer with FastAPI and LangChain experience.');
      formData.append('text', 'Candidate with 5 years experience in Python, FastAPI, and building LLM agents.');

      const response = await fetch('http://127.0.0.1:8000/resume/analyze_with_jd', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      setCandidateId(data.candidate_id);
      
      // For demo, we just wait 3 seconds for pre-gen
      setTimeout(() => {
        setIsPreGenerating(false);
      }, 3000);
    } catch (e) {
      console.error('Upload failed', e);
      setIsPreGenerating(false);
    }
  };

  const handleToggleConnection = useCallback(() => {
    if (isConnected) {
      disconnect();
      setMicActive(false);
    } else {
      setIsConnecting(true);
      connect();
    }
  }, [isConnected, disconnect, connect]);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-slate-900 text-white p-8">
      <div className="w-full max-w-4xl bg-slate-800 rounded-3xl p-12 shadow-2xl border border-slate-700 flex flex-col items-center gap-8">
        <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
          Project Raven
        </h1>
        
        {/* Step 1: Upload */}
        {!candidateId && !isPreGenerating && (
          <div className="flex flex-col items-center gap-4">
            <p className="text-slate-300">Welcome! Please upload your resume to begin.</p>
            <button 
              onClick={handleUpload}
              className="px-8 py-3 bg-blue-600 hover:bg-blue-700 rounded-full font-semibold transition-all"
            >
              Analyze Resume (Demo Mode)
            </button>
          </div>
        )}

        {/* Step 2: Pre-generating */}
        {isPreGenerating && (
          <div className="flex flex-col items-center gap-4">
            <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-blue-400 animate-pulse">Building your interview profile...</p>
          </div>
        )}

        {/* Step 3: Interview Room */}
        {candidateId && !isPreGenerating && (
          <>
            <div className="flex gap-4 items-center">
              <span className="px-3 py-1 bg-green-500/20 text-green-400 border border-green-500/30 rounded-full text-xs font-mono">
                Session: {candidateId.slice(0, 8)}
              </span>
              <span className="px-3 py-1 bg-blue-500/20 text-blue-400 border border-blue-500/30 rounded-full text-xs font-mono uppercase">
                View: {currentView}
              </span>
            </div>

            <div className="relative w-48 h-48 flex items-center justify-center">
              <VoiceVisualizer isActive={micActive} isMuted={isMicMuted} />
            </div>

            {currentView === 'monaco' && (
              <div className="w-full h-64 bg-black rounded-xl border border-slate-700 p-4 font-mono text-sm text-green-400 overflow-hidden relative">
                <div className="absolute top-2 right-4 text-xs text-slate-500 uppercase">Monaco Editor Mockup</div>
                <p># Solve the Two Sum problem</p>
                <p>def solve(nums, target):</p>
                <p className="animate-pulse">|</p>
              </div>
            )}

            <div className="flex flex-wrap justify-center gap-6">
              <button
                onClick={handleToggleConnection}
                disabled={isConnecting}
                className={`px-8 py-4 rounded-full font-semibold transition-all shadow-lg ${
                  isConnected ? 'bg-red-600 hover:bg-red-700' : 'bg-blue-600 hover:bg-blue-700'
                }`}
              >
                {isConnecting ? 'Connecting...' : isConnected ? 'End Interview' : 'Start Interview'}
              </button>

              {isConnected && (
                <button
                  onClick={() => setIsMicMuted(!isMicMuted)}
                  className={`p-4 rounded-full transition-all border ${
                    isMicMuted ? 'bg-slate-700 border-red-500 text-red-500' : 'bg-slate-700 border-slate-600'
                  }`}
                >
                  {isMicMuted ? 'Mic Muted' : 'Mic Active'}
                </button>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default InterviewRoom;
