"use client";

import { useState } from 'react';
import Link from 'next/link';

export default function CandidateView() {
  const [roomCodeInput, setRoomCodeInput] = useState('');
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [hasJoined, setHasJoined] = useState(false);
  const [isJoining, setIsJoining] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const joinRoom = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!roomCodeInput || !resumeFile) return;
    
    setIsJoining(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("roomCode", roomCodeInput);
      formData.append("resume", resumeFile);

      // We assume backend runs on localhost:8000 for local dev
      const res = await fetch("http://localhost:8000/api/rooms/join", {
        method: "POST",
        body: formData,
      });
      
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to join room");
      
      setSessionId(data.sessionId);
      setHasJoined(true);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsJoining(false);
    }
  };

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-surface relative">
      {/* Join Room Modal Overlay */}
      {!hasJoined && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-md">
          <div className="bg-surface-container-lowest border-hard shadow-hard p-xl flex flex-col items-center max-w-md w-full gap-lg relative">
            <h2 className="font-h1 text-h1 text-primary font-bold text-center">Join Interview</h2>
            <p className="font-body text-body text-secondary text-center">Enter the room code provided by your interviewer and upload your resume.</p>
            
            <form onSubmit={joinRoom} className="w-full flex flex-col gap-md">
              <input 
                type="text" 
                placeholder="Room Code (e.g. A7B29)"
                value={roomCodeInput}
                onChange={(e) => setRoomCodeInput(e.target.value.toUpperCase())}
                className="w-full border-hard p-sm font-code text-primary focus:outline-none focus:ring-2 focus:ring-primary"
                required
              />
              <div className="w-full border-hard border-dashed p-md flex flex-col items-center justify-center text-secondary hover:bg-surface-container-low transition-all cursor-pointer relative">
                <span className="material-symbols-outlined mb-xs text-h2">upload_file</span>
                <span className="font-label-caps text-label-caps text-center">
                  {resumeFile ? resumeFile.name : "UPLOAD RESUME (PDF)"}
                </span>
                <input 
                  type="file" 
                  accept=".pdf"
                  onChange={(e) => setResumeFile(e.target.files?.[0] || null)}
                  className="absolute inset-0 opacity-0 cursor-pointer"
                  required
                />
              </div>
              
              {error && <p className="text-error font-body text-sm text-center">{error}</p>}
              
              <button 
                type="submit"
                disabled={isJoining || !roomCodeInput || !resumeFile}
                className="border-hard bg-primary text-on-primary p-md w-full shadow-hard-hover flex items-center justify-center font-label-caps text-label-caps transition-all disabled:opacity-50 mt-sm"
              >
                {isJoining ? "JOINING..." : "JOIN ROOM"}
              </button>
            </form>
            <Link href="/" className="absolute top-sm right-sm text-secondary hover:text-primary">
              <span className="material-symbols-outlined">close</span>
            </Link>
          </div>
        </div>
      )}

      {/* TopAppBar */}
      <header className="bg-surface dark:bg-surface text-primary dark:text-primary font-h2 text-h2 w-full top-0 border-b-[1.5px] border-primary dark:border-primary flex justify-between items-center px-md py-sm shrink-0 z-20">
        <div className="flex items-center gap-sm">
          <div className="w-8 h-8 bg-primary text-on-primary flex items-center justify-center font-bold text-body">R</div>
          <div className="font-h1 text-h1 font-bold text-primary dark:text-primary">Project Raven</div>
        </div>
        <div className="flex items-center gap-md">
          <div className="font-label-caps text-label-caps flex items-center gap-xs">
            <span className="w-2 h-2 rounded-full bg-primary block"></span>
            System: {hasJoined ? 'Connected' : 'Waiting...'}
          </div>
          <div className="flex gap-sm">
            <Link href="/" className="w-10 h-10 border-hard flex items-center justify-center hover:bg-secondary-container transition-all text-primary">
              <span className="material-symbols-outlined">settings</span>
            </Link>
            <button className="w-10 h-10 border-hard flex items-center justify-center hover:bg-secondary-container transition-all">
              <span className="material-symbols-outlined">account_circle</span>
            </button>
          </div>
        </div>
      </header>
      
      {/* Canvas Area */}
      <main className="flex-1 flex p-gutter gap-gutter overflow-hidden relative z-10">
        {/* Left Panel (Problem & Code) */}
        <div className="w-[60%] flex flex-col h-full gap-gutter">
          {/* Problem Statement & Editor Block */}
          <div className="border-hard bg-surface-container-lowest p-md flex flex-col shadow-hard h-full">
            <div className="border-b-[1.5px] border-primary pb-sm mb-md flex justify-between items-center shrink-0">
              <h2 className="font-h2 text-h2 text-primary font-bold">Problem Statement: Sum of Primes</h2>
              <div className="font-label-caps text-label-caps text-secondary px-sm py-xs border-hard font-medium">EASY</div>
            </div>
            <div className="font-body text-body text-on-surface mb-md shrink-0">
              <p className="mb-sm">Write a function that takes an integer <code>n</code> and returns the sum of all prime numbers less than or equal to <code>n</code>.</p>
              <p><strong>Constraints:</strong> <code>0 &lt;= n &lt;= 10^6</code></p>
            </div>
            {/* Code Editor Mockup */}
            <div className="border-hard bg-editor flex-1 flex flex-col min-h-[300px]">
              <div className="border-b-[1.5px] border-primary p-xs flex gap-xs bg-surface-container-high shrink-0">
                <div className="bg-primary text-on-primary px-sm py-xs font-label-caps text-label-caps border-hard">main.py</div>
                <div className="text-primary px-sm py-xs font-label-caps text-label-caps border-transparent border-b-primary border-b-[1.5px] hover:bg-surface-container-low cursor-pointer">tests.py</div>
              </div>
              <div className="flex flex-1 p-sm font-code text-code text-on-surface overflow-y-auto font-medium">
                <div className="w-8 text-right pr-sm border-r-[1.5px] border-primary text-secondary select-none">
                  1<br/>2<br/>3<br/>4<br/>5
                </div>
                <div className="pl-sm flex-1 whitespace-pre">
{`def sum_of_primes(n: int) -> int:
    # Your code here
    pass`}
                </div>
              </div>
            </div>
          </div>
        </div>
        
        {/* Right Panel (Agent Interface & Transcript) */}
        <div className="w-[40%] flex flex-col gap-gutter h-full">
          {/* Agent Visualization Block */}
          <div className="border-hard h-[45%] flex flex-col shadow-hard relative overflow-hidden shrink-0 bg-surface-container-lowest">
            <div className="p-sm border-b-[1.5px] border-primary flex justify-between items-center z-10 bg-surface-container-lowest shrink-0">
              <span className="font-label-caps text-label-caps text-primary">RAVEN AGENT V2.4</span>
              <div className="flex items-center gap-xs">
                <span className={`w-2 h-2 rounded-full ${hasJoined ? 'bg-[#0f0] animate-pulse' : 'bg-secondary'}`}></span>
                <span className={`font-label-caps text-label-caps ${hasJoined ? 'text-[#0f0]' : 'text-secondary'}`}>
                  {hasJoined ? 'LISTENING' : 'OFFLINE'}
                </span>
              </div>
            </div>
            <div className="flex-1 relative flex items-center justify-center p-md">
              <div className="flex flex-col items-center justify-center w-full h-full gap-lg">
                <div className="flex items-end gap-xs h-24 justify-center">
                  <div className={`w-1.5 bg-primary rounded-full ${hasJoined ? 'animate-[bounce_1s_infinite]' : ''}`} style={{ height: hasJoined ? '40%' : '5%' }}></div>
                  <div className={`w-1.5 bg-primary rounded-full ${hasJoined ? 'animate-[bounce_1.2s_infinite]' : ''}`} style={{ height: hasJoined ? '70%' : '5%' }}></div>
                  <div className={`w-1.5 bg-primary rounded-full ${hasJoined ? 'animate-[bounce_0.8s_infinite]' : ''}`} style={{ height: hasJoined ? '50%' : '5%' }}></div>
                  <div className={`w-1.5 bg-primary rounded-full ${hasJoined ? 'animate-[bounce_1.5s_infinite]' : ''}`} style={{ height: hasJoined ? '90%' : '5%' }}></div>
                  <div className={`w-1.5 bg-primary rounded-full ${hasJoined ? 'animate-[bounce_1.1s_infinite]' : ''}`} style={{ height: hasJoined ? '60%' : '5%' }}></div>
                  <div className={`w-1.5 bg-primary rounded-full ${hasJoined ? 'animate-[bounce_0.9s_infinite]' : ''}`} style={{ height: hasJoined ? '80%' : '5%' }}></div>
                  <div className={`w-1.5 bg-primary rounded-full ${hasJoined ? 'animate-[bounce_1.3s_infinite]' : ''}`} style={{ height: hasJoined ? '45%' : '5%' }}></div>
                  <div className={`w-1.5 bg-primary rounded-full ${hasJoined ? 'animate-[bounce_1s_infinite]' : ''}`} style={{ height: hasJoined ? '65%' : '5%' }}></div>
                </div>
                <div className="text-center">
                  <p className="font-label-caps text-label-caps text-secondary">
                    {hasJoined ? 'AI VOICE INTERFACE ACTIVE' : 'WAITING TO JOIN ROOM'}
                  </p>
                </div>
              </div>
            </div>
            {/* Interview Controls */}
            <div className="p-sm border-t-[1.5px] border-primary z-10 bg-surface-container-lowest grid grid-cols-2 gap-sm shrink-0">
              <button disabled={!hasJoined} className="bg-white text-primary font-label-caps text-label-caps p-sm border-hard shadow-hard-hover flex items-center justify-center gap-xs disabled:opacity-50">
                <span className="material-symbols-outlined">mic_off</span>
                MUTE
              </button>
              <button disabled={!hasJoined} className="bg-error text-on-error font-label-caps text-label-caps p-sm border-hard shadow-hard-hover flex items-center justify-center gap-xs disabled:opacity-50">
                <span className="material-symbols-outlined">call_end</span>
                END
              </button>
            </div>
          </div>
          
          {/* Live Transcript Block */}
          <div className="border-hard bg-surface-container-lowest p-md flex flex-col shadow-hard flex-1 min-h-0">
            <div className="border-b-[1.5px] border-primary pb-sm mb-sm shrink-0">
              <h2 className="font-label-caps text-label-caps text-primary">Live Transcript</h2>
            </div>
            <div className="flex-1 overflow-y-auto flex flex-col gap-lg font-mono-body text-mono-body">
              {hasJoined ? (
                <>
                  {/* Agent Message */}
                  <div className="flex flex-col gap-xs">
                    <div className="w-8 h-8 bg-primary text-on-primary flex items-center justify-center font-bold border-hard shrink-0">R</div>
                    <div className="p-sm text-on-surface rounded-none w-full font-semibold text-lg">
                      Hello Candidate. Let's begin. Can you explain your initial approach to the 'Sum of Primes' problem?
                    </div>
                  </div>
                  {/* Candidate Message */}
                  <div className="flex gap-sm items-start flex-row-reverse">
                    <div className="w-8 h-8 bg-surface-container-high border-hard flex items-center justify-center shrink-0">
                      <span className="material-symbols-outlined">person</span>
                    </div>
                    <div className="bg-surface-container-low p-sm border-hard text-on-surface rounded-none max-w-[85%] font-medium text-lg">
                      Hi. Yes, I'm thinking of using the Sieve of Eratosthenes to efficiently find all primes up to n, and then sum them up.
                    </div>
                  </div>
                </>
              ) : (
                <div className="h-full flex items-center justify-center">
                  <p className="text-secondary text-center">Transcript will appear here once connected.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
