'use client';

import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useVoiceWebSocket } from '../hooks/useVoiceWebSocket';
import VoiceVisualizer from './VoiceVisualizer';
import CodeEditor from './CodeEditor';
import SkillsView from './SkillsView';
import ReportView from './ReportView';
import {
  AlertCircle, Loader2, Terminal,
  Briefcase, Mic, MicOff, ChevronRight, LayoutDashboard,
  Upload, CheckCircle2,
} from 'lucide-react';

const InterviewRoom: React.FC = () => {
  // ── Setup state ─────────────────────────────────────────────────────────────
  const [candidateId, setCandidateId] = useState<string | null>(null);
  const [candidateName, setCandidateName] = useState<string | null>(null);
  const [isPreGenerating, setIsPreGenerating] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [currentView, setCurrentView] = useState('avatar');
  const [currentStage, setCurrentStage] = useState('INTRO');
  const [matchedSkills, setMatchedSkills] = useState<any[]>([]);
  const [codeGrade, setCodeGrade] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [jdText, setJdText] = useState('Seeking a Software Engineer to build agentic workflows with LangGraph and Gemini.');
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [isGrading, setIsGrading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

  // ── Voice hook ──────────────────────────────────────────────────────────────
  const {
    status,
    connect,
    disconnect,
    toggleMute,
    isMuted,
    inputAmplitude,
    outputAmplitude,
    sendUIReady,
    sendCode,
    errorMessage,
  } = useVoiceWebSocket({
    onUIEvent: (view, stage) => {
      setCurrentView(view);
      if (stage) setCurrentStage(stage);
      // Send ui_ready after the component mounts (200ms for DOM paint)
      setTimeout(() => sendUIReady(stage || view), 200);
    },
    onInterrupted: () => {
      // Optional: add visual flash/feedback here
    },
    onCodeReceived: () => {
      setIsGrading(true);
    },
    onFinished: () => {
      setCurrentView('report');
    },
  });

  // Sync hook error to local state
  useEffect(() => {
    if (errorMessage) setError(errorMessage);
  }, [errorMessage]);

  // ── Poll /status until ready ────────────────────────────────────────────────
  useEffect(() => {
    if (!candidateId || !isPreGenerating) return;
    let delay = 1500;
    let timeoutId: NodeJS.Timeout;

    const poll = async () => {
      try {
        const res = await fetch(`${backendUrl}/status/${candidateId}`);
        const data = await res.json();

        if (data.status === 'ready') {
          setIsPreGenerating(false);
          setIsReady(true);
          setCurrentStage(data.current_stage || 'INTRO');
          setMatchedSkills(data.matched_skills || []);
          if (data.candidate_name) setCandidateName(data.candidate_name);
          if (data.code_grade) { setCodeGrade(data.code_grade); setIsGrading(false); }
        } else if (data.status === 'error') {
          setIsPreGenerating(false);
          setError(data.error_message || 'Analysis failed. Please try again.');
        } else {
          // Still processing — poll again with exponential backoff (max 5s)
          delay = Math.min(delay * 1.5, 5000);
          timeoutId = setTimeout(poll, delay);
        }
      } catch {
        timeoutId = setTimeout(poll, delay);
      }
    };

    timeoutId = setTimeout(poll, delay);
    return () => clearTimeout(timeoutId);
  }, [candidateId, isPreGenerating, backendUrl]);

  // Also poll code_grade once grading starts
  useEffect(() => {
    if (!candidateId || !isGrading) return;
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${backendUrl}/status/${candidateId}`);
        const data = await res.json();
        if (data.code_grade) {
          setCodeGrade(data.code_grade);
          setIsGrading(false);
          clearInterval(interval);
        }
      } catch { /* retry */ }
    }, 1500);
    return () => clearInterval(interval);
  }, [candidateId, isGrading, backendUrl]);

  // ── Upload handler ──────────────────────────────────────────────────────────
  const handleUpload = async () => {
    if (!resumeFile) {
      setError('Please select a resume PDF before starting.');
      return;
    }
    if (!jdText.trim()) {
      setError('Please provide a job description.');
      return;
    }
    setError(null);
    setIsPreGenerating(true);

    try {
      const formData = new FormData();
      formData.append('jd_text', jdText);
      formData.append('file', resumeFile);

      const response = await fetch(`${backendUrl}/resume/analyze_with_jd`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || `Server error ${response.status}`);
      }

      const data = await response.json();
      setCandidateId(data.candidate_id);
    } catch (e: any) {
      setError(e.message || 'Backend offline. Check if the server is running.');
      setIsPreGenerating(false);
    }
  };

  const handleToggleConnection = useCallback(() => {
    if (status === 'connected' || status === 'listening' || status === 'speaking') {
      disconnect();
    } else if (candidateId) {
      connect(candidateId);
    }
  }, [status, disconnect, connect, candidateId]);

  const isConnected = !['idle', 'connecting', 'error', 'finished'].includes(status);

  // ─────────────────────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-[#020617] text-slate-200 p-4 md:p-8 font-sans selection:bg-blue-500/30">
      <div className={`w-full max-w-5xl bg-[#0f172a]/80 backdrop-blur-3xl rounded-[3rem] p-8 md:p-14 shadow-[0_32px_128px_-24px_rgba(0,0,0,0.8)] border border-slate-800/50 flex flex-col items-center transition-all duration-1000 ${currentView === 'monaco' ? 'max-w-6xl' : ''}`}>

        {/* Header */}
        <div className="flex items-center justify-between w-full mb-16">
          <div className="flex items-center gap-4 group cursor-default">
            <div className="w-12 h-12 bg-blue-600 rounded-2xl flex items-center justify-center shadow-2xl shadow-blue-600/30 group-hover:scale-110 transition-transform">
              <LayoutDashboard size={24} className="text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-black tracking-tight text-white uppercase italic">RAVEN</h1>
              <div className="h-0.5 w-8 bg-blue-600 rounded-full" />
            </div>
          </div>

          {candidateId && (
            <div className="flex items-center gap-3">
              <div className="flex flex-col items-end">
                {candidateName && (
                  <span className="text-xs font-bold text-white">{candidateName}</span>
                )}
                <span className="text-[10px] font-black text-blue-500 uppercase tracking-widest">{currentStage}</span>
                <span className="text-[10px] font-bold text-slate-500 font-mono">ID: {candidateId.slice(0, 8)}</span>
              </div>
            </div>
          )}
        </div>

        {/* Error banner */}
        {error && (
          <div className="w-full mb-10 p-5 bg-red-500/5 border border-red-500/20 rounded-[2rem] flex items-center gap-4 text-red-400 text-sm animate-in slide-in-from-top-4 duration-500">
            <AlertCircle size={22} className="shrink-0" />
            <p className="font-medium">{error}</p>
            <button onClick={() => setError(null)} className="ml-auto text-red-500 hover:text-red-300 text-lg">×</button>
          </div>
        )}

        <div className="w-full flex flex-col items-center gap-14 flex-1">

          {/* ── Setup screen (no candidate ID yet) ───────────────────────── */}
          {!candidateId && !isPreGenerating && (
            <div className="flex flex-col items-center gap-10 py-8 text-center max-w-2xl w-full">
              <div className="space-y-4">
                <h2 className="text-5xl font-black text-white leading-tight uppercase italic tracking-tighter">
                  Initialize <span className="text-blue-500">Raven</span>
                </h2>
                <p className="text-slate-400 text-lg font-medium leading-relaxed">
                  Upload your resume and provide the job description to begin the AI assessment.
                </p>
              </div>

              <div className="w-full grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* JD input */}
                <div className="flex flex-col items-start gap-3">
                  <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest ml-2">Job Description</span>
                  <textarea
                    value={jdText}
                    onChange={(e) => setJdText(e.target.value)}
                    placeholder="Paste the Job Description here..."
                    className="w-full h-40 bg-slate-900/50 border border-slate-800 rounded-3xl p-5 text-sm text-slate-300 focus:border-blue-500 outline-none transition-all resize-none"
                  />
                </div>

                {/* Resume upload */}
                <div className="flex flex-col items-start gap-3">
                  <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest ml-2">Candidate Resume (PDF) *required</span>
                  <div
                    onClick={() => fileInputRef.current?.click()}
                    className={`w-full h-40 border-2 border-dashed rounded-3xl flex flex-col items-center justify-center gap-3 cursor-pointer transition-all ${
                      resumeFile
                        ? 'bg-blue-500/10 border-blue-500'
                        : 'bg-slate-900/50 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <input
                      type="file"
                      ref={fileInputRef}
                      onChange={(e) => { setResumeFile(e.target.files?.[0] || null); setError(null); }}
                      className="hidden"
                      accept=".pdf"
                    />
                    {resumeFile ? (
                      <>
                        <CheckCircle2 size={32} className="text-blue-400" />
                        <span className="text-xs font-bold text-blue-400">{resumeFile.name}</span>
                      </>
                    ) : (
                      <>
                        <Upload size={32} className="text-slate-600" />
                        <span className="text-xs font-bold text-slate-500">Click to select PDF</span>
                      </>
                    )}
                  </div>
                </div>
              </div>

              <button
                onClick={handleUpload}
                disabled={!resumeFile}
                className="group relative px-14 py-6 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 disabled:cursor-not-allowed rounded-3xl font-black text-xl text-white transition-all shadow-2xl shadow-blue-600/30 active:scale-95 mt-4"
              >
                <div className="flex items-center gap-3">
                  Start Analysis <ChevronRight size={20} />
                </div>
              </button>
            </div>
          )}

          {/* ── Pre-generation loading ─────────────────────────────────────── */}
          {isPreGenerating && (
            <div className="flex flex-col items-center gap-8 py-24">
              <div className="relative h-20 w-20">
                <Loader2 size={80} className="text-blue-500 animate-spin" />
                <div className="absolute inset-0 blur-3xl bg-blue-500/30 rounded-full animate-pulse" />
              </div>
              <div className="text-center space-y-3">
                <p className="text-2xl font-black text-white uppercase tracking-tighter">Initializing Agent...</p>
                <p className="text-slate-500 font-mono text-xs uppercase tracking-widest">Scanning skillset · Generating question bank</p>
              </div>
            </div>
          )}

          {/* ── Interview room (session active) ───────────────────────────── */}
          {candidateId && isReady && (
            <div className="w-full flex flex-col items-center gap-14">

              {/* Avatar / Skills view */}
              {currentView === 'avatar' && (
                <div className="flex flex-col items-center gap-12 w-full animate-in fade-in duration-1000">
                  <div className="relative w-72 h-72 md:w-96 md:h-96 flex items-center justify-center">
                    <VoiceVisualizer
                      isActive={status === 'listening' || status === 'speaking'}
                      isMuted={isMuted}
                      amplitude={status === 'speaking' ? outputAmplitude : inputAmplitude}
                      isSpeaking={status === 'speaking'}
                    />
                  </div>
                  {matchedSkills.length > 0 && <SkillsView skills={matchedSkills} />}
                </div>
              )}

              {/* Code editor view */}
              {currentView === 'monaco' && (
                <div className="w-full flex flex-col items-center gap-10 animate-in zoom-in-95 duration-700">
                  <div className="w-full h-[550px]">
                    <CodeEditor
                      language={currentStage === 'SQL' ? 'sql' : 'python'}
                      defaultCode={currentStage === 'SQL' ? '-- Write your SQL query here\n' : '# Write your solution here\n'}
                      onSubmit={(code) => sendCode(code)}
                      isGrading={isGrading}
                    />
                  </div>
                  <div className="flex items-center gap-4 text-slate-500 text-[10px] font-black uppercase tracking-[0.2em] bg-slate-900/50 px-6 py-2 rounded-full border border-slate-800">
                    <Terminal size={14} className="text-blue-500" />
                    <span>{isGrading ? 'Raven is reviewing your code...' : 'Neural Feedback Buffer: Active'}</span>
                    {isGrading && <Loader2 size={12} className="animate-spin text-blue-500" />}
                  </div>
                </div>
              )}

              {/* Report view */}
              {currentView === 'report' && (
                <ReportView grade={codeGrade} />
              )}

              {/* Controls */}
              <div className="flex flex-wrap justify-center gap-6 pt-12 border-t border-slate-800/50 w-full">
                <button
                  onClick={handleToggleConnection}
                  disabled={status === 'connecting'}
                  className={`flex items-center gap-4 px-12 py-5 rounded-[2rem] font-black uppercase tracking-tighter transition-all shadow-2xl active:scale-95 ${
                    isConnected
                      ? 'bg-red-500/10 text-red-500 border border-red-500/20 hover:bg-red-600 hover:text-white'
                      : 'bg-white text-black hover:bg-blue-600 hover:text-white shadow-blue-600/10'
                  }`}
                >
                  {status === 'connecting' ? (
                    <><Loader2 size={20} className="animate-spin" /> Connecting</>
                  ) : isConnected ? (
                    'End Session'
                  ) : (
                    'Start Interview'
                  )}
                </button>

                {isConnected && (
                  <button
                    onClick={toggleMute}
                    className={`p-5 rounded-[2rem] transition-all border shadow-xl ${
                      isMuted
                        ? 'bg-red-500/10 border-red-500/20 text-red-500'
                        : 'bg-slate-800/50 border-slate-700 text-slate-400 hover:border-blue-500 hover:text-blue-500'
                    }`}
                  >
                    {isMuted ? <MicOff size={24} /> : <Mic size={24} />}
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default InterviewRoom;
