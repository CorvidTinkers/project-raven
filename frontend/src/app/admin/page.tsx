"use client";

import { useState } from 'react';
import Link from 'next/link';

export default function AdminDashboard() {
  const [roomCode, setRoomCode] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generateRoom = async () => {
    setIsGenerating(true);
    setError(null);
    try {
      const res = await fetch("http://localhost:8000/api/rooms/create", {
        method: "POST"
      });
      if (!res.ok) throw new Error("Failed to create room");
      const data = await res.json();
      setRoomCode(data.roomCode);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopy = () => {
    if (roomCode) {
      navigator.clipboard.writeText(roomCode);
      alert("Room code copied to clipboard!");
    }
  };

  return (
    <div className="bg-surface text-on-surface font-body text-body h-screen flex overflow-hidden w-full relative">
      
      {/* Room Generation Modal Overlay */}
      {!roomCode && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-md">
          <div className="bg-surface-container-lowest border-hard shadow-hard p-xl flex flex-col items-center max-w-md w-full gap-lg relative">
            <h2 className="font-h1 text-h1 text-primary font-bold text-center">Initialize Interview</h2>
            <p className="font-body text-body text-secondary text-center">Generate a secure room code to share with the candidate.</p>
            {error && <p className="text-error font-body">{error}</p>}
            <button 
              onClick={generateRoom}
              disabled={isGenerating}
              className="border-hard bg-primary text-on-primary p-md w-full shadow-hard-hover flex items-center justify-center font-label-caps text-label-caps transition-all disabled:opacity-50 mt-sm"
            >
              {isGenerating ? "GENERATING..." : "GENERATE NEW ROOM"}
            </button>
            <Link href="/" className="absolute top-sm right-sm text-secondary hover:text-primary">
              <span className="material-symbols-outlined">close</span>
            </Link>
          </div>
        </div>
      )}

      {/* SideNavBar */}
      <nav className="bg-surface border-r-[1.5px] border-primary z-40 fixed left-0 top-0 h-full flex flex-col w-64 hidden md:flex shrink-0">
        <div className="px-md py-xl border-b-[1.5px] border-primary">
          <div className="flex items-center gap-sm mb-xs">
            <div className="w-8 h-8 bg-primary text-on-primary flex items-center justify-center font-bold text-body shrink-0">R</div>
            <h1 className="font-h2 text-h2 font-bold text-primary tracking-tight">RAVEN</h1>
          </div>
          <p className="font-label-caps text-label-caps text-secondary">Technical Assessment</p>
        </div>
        <div className="flex-1 p-md space-y-sm">
          <a className="flex items-center gap-md px-md py-sm bg-primary text-on-primary font-label-caps text-label-caps border-hard" href="#">
            <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>dashboard</span>
            <span>Dashboard</span>
          </a>
          <a className="flex items-center gap-md px-md py-sm text-primary hover:bg-surface-container-high transition-none font-label-caps text-label-caps border-[1.5px] border-transparent hover:border-primary" href="#">
            <span className="material-symbols-outlined">person_search</span>
            <span>Candidate</span>
          </a>
          <a className="flex items-center gap-md px-md py-sm text-primary hover:bg-surface-container-high transition-none font-label-caps text-label-caps border-[1.5px] border-transparent hover:border-primary" href="#">
            <span className="material-symbols-outlined">receipt_long</span>
            <span>Logs</span>
          </a>
          <a className="flex items-center gap-md px-md py-sm text-primary hover:bg-surface-container-high transition-none font-label-caps text-label-caps border-[1.5px] border-transparent hover:border-primary" href="#">
            <span className="material-symbols-outlined">grading</span>
            <span>Evaluation</span>
          </a>
        </div>
      </nav>

      {/* Main Content Canvas */}
      <main className="flex-1 flex flex-col ml-0 md:ml-64 relative h-full w-full">
        {/* TopAppBar (Mobile Only) */}
        <header className="bg-surface border-b-[1.5px] border-primary flex justify-between items-center w-full px-md h-16 mx-auto md:hidden z-30 shrink-0">
          <h1 className="font-h2 text-h2 font-bold tracking-tight text-primary">
            RAVEN {roomCode && <span className="ml-sm text-secondary font-code text-lg">Room: {roomCode}</span>}
          </h1>
          <div className="flex items-center gap-md">
            <button className="w-10 h-10 border-hard flex items-center justify-center hover:bg-secondary-container transition-all text-primary"><span className="material-symbols-outlined">monitoring</span></button>
            <button className="w-10 h-10 border-hard flex items-center justify-center hover:bg-secondary-container transition-all text-primary"><span className="material-symbols-outlined">history</span></button>
            <Link href="/" className="w-10 h-10 border-hard flex items-center justify-center hover:bg-secondary-container transition-all text-primary"><span className="material-symbols-outlined">settings</span></Link>
          </div>
        </header>

        {/* TopAppBar (Web - Adjusted for SideNav context) */}
        <header className="bg-surface border-b-[1.5px] border-primary hidden md:flex justify-between items-center w-full px-gutter h-16 z-30 shrink-0">
          <h1 className="font-h2 text-h2 font-bold tracking-tight text-primary flex items-center gap-md">
            PROJECT RAVEN 
            {roomCode && (
              <div className="flex items-center bg-surface-container-low px-sm py-xs border-hard ml-sm">
                <span className="font-code text-lg text-primary mr-sm">Room: {roomCode}</span>
                <button onClick={handleCopy} className="text-secondary hover:text-primary transition-colors flex items-center">
                  <span className="material-symbols-outlined text-sm">content_copy</span>
                </button>
              </div>
            )}
          </h1>
          <div className="flex items-center gap-sm">
            <button className="w-10 h-10 border-hard flex items-center justify-center hover:bg-secondary-container transition-all text-primary"><span className="material-symbols-outlined">monitoring</span></button>
            <button className="w-10 h-10 border-hard flex items-center justify-center hover:bg-secondary-container transition-all text-primary"><span className="material-symbols-outlined">history</span></button>
            <Link href="/" className="w-10 h-10 border-hard flex items-center justify-center hover:bg-secondary-container transition-all text-primary"><span className="material-symbols-outlined">settings</span></Link>
          </div>
        </header>

        {/* Dashboard Content */}
        <div className="flex-1 overflow-y-auto p-gutter space-y-gutter w-full flex flex-col">
          {/* Agent Status Header */}
          <section className="flex flex-col md:flex-row justify-between items-start md:items-center gap-gutter border-hard p-md bg-surface-container-lowest shadow-hard shrink-0">
            <div>
              <h2 className="font-h2 text-h2 font-bold text-primary mb-xs">
                {roomCode ? "Waiting for Candidate..." : "No Active Session"}
              </h2>
              <p className="font-mono-body text-mono-body text-secondary">
                {roomCode ? "Session pending join" : "Generate a room to begin"}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-sm">
              <div className="bg-surface-container-low px-md py-sm border-hard flex items-center gap-sm">
                <div className={`w-2 h-2 ${roomCode ? 'bg-secondary' : 'bg-secondary'}`}></div>
                <span className="font-label-caps text-label-caps text-primary">OFFLINE</span>
              </div>
              <button disabled={!roomCode} className="bg-primary text-on-primary border-hard px-md py-sm font-label-caps text-label-caps shadow-hard-hover disabled:opacity-50">INTERVENE</button>
              <button disabled={!roomCode} className="bg-surface text-primary border-hard px-md py-sm font-label-caps text-label-caps shadow-hard-hover disabled:opacity-50">PAUSE</button>
              <button disabled={!roomCode} className="bg-error text-on-error border-hard px-md py-sm font-label-caps text-label-caps shadow-hard-hover disabled:opacity-50">END</button>
            </div>
          </section>

          {/* Grid Layout Top Section */}
          <div className={`grid grid-cols-1 xl:grid-cols-3 gap-gutter shrink-0 transition-opacity ${!roomCode ? 'opacity-50 pointer-events-none' : ''}`}>
            {/* Left Column: Metrics */}
            <div className="xl:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-gutter h-max">
              {/* Metric Card 1 */}
              <div className="border-hard bg-surface-container-lowest flex flex-col shadow-hard p-sm">
                <div className="flex justify-between items-start border-b-[1.5px] border-primary pb-sm mb-xs">
                  <span className="font-label-caps text-label-caps text-primary">Technical Depth</span>
                  <span className="material-symbols-outlined text-primary text-sm">trending_up</span>
                </div>
                <div>
                  <div className="font-h1 text-primary font-bold text-h2">--</div>
                  <p className="font-body text-body text-on-surface mt-xs">Awaiting data...</p>
                </div>
              </div>
              {/* Metric Card 2 */}
              <div className="border-hard bg-surface-container-lowest flex flex-col shadow-hard p-sm">
                <div className="flex justify-between items-start border-b-[1.5px] border-primary pb-sm mb-xs">
                  <span className="font-label-caps text-label-caps text-primary">Communication</span>
                  <span className="material-symbols-outlined text-primary text-sm">trending_flat</span>
                </div>
                <div>
                  <div className="font-h1 text-primary font-bold text-h2">--</div>
                  <p className="font-body text-body text-on-surface mt-xs">Awaiting data...</p>
                </div>
              </div>
              {/* Metric Card 3 */}
              <div className="border-hard bg-surface-container-lowest flex flex-col shadow-hard p-sm">
                <div className="flex justify-between items-start border-b-[1.5px] border-primary pb-sm mb-xs">
                  <span className="font-label-caps text-label-caps text-primary">Problem Solving</span>
                  <span className="material-symbols-outlined text-primary text-sm">trending_up</span>
                </div>
                <div>
                  <div className="font-h1 text-primary font-bold text-h2">--</div>
                  <p className="font-body text-body text-on-surface mt-xs">Awaiting data...</p>
                </div>
              </div>
              {/* Metric Card 4 */}
              <div className="border-hard bg-surface-container-lowest flex flex-col shadow-hard p-sm">
                <div className="flex justify-between items-start border-b-[1.5px] border-primary pb-sm mb-xs">
                  <span className="font-label-caps text-label-caps text-primary">SQL/DSA Correctness</span>
                  <span className="material-symbols-outlined text-error text-sm">trending_down</span>
                </div>
                <div>
                  <div className="font-h1 text-primary font-bold text-h2">--</div>
                  <p className="font-body text-body text-on-surface mt-xs">Awaiting data...</p>
                </div>
              </div>
            </div>

            {/* Right Column: Agent View & Notes */}
            <div className="flex flex-col gap-gutter h-full">
              {/* Agent Waveform */}
              <div className="border-hard bg-surface-container-lowest flex flex-col shadow-hard relative overflow-hidden min-h-[200px] shrink-0">
                <div className="p-sm border-b-[1.5px] border-primary flex justify-between items-center z-10 bg-surface-container-lowest">
                  <span className="font-label-caps text-label-caps text-primary">AUDIO FEED</span>
                  <span className="material-symbols-outlined text-primary text-sm">mic</span>
                </div>
                <div className="flex-1 relative flex items-center justify-center p-md bg-[#131313]">
                  <img alt="Agent Waveform Visualization" className="absolute inset-0 w-3/4 h-3/4 object-contain mx-auto my-auto opacity-100 invert" data-alt="A minimalist digital art waveform consisting of clean, sharp black lines oscillating against a pure white background. The visual represents an active AI voice agent processing audio. The style is stark, modern, and highly contrasted, fitting a strict black-and-white professional UI aesthetic." src="https://lh3.googleusercontent.com/aida/ADBb0ujx4191_ElIQGqeaCv3VNT5Hf9WPNSygjfUzpEUFKSkLeciqvhf_0uYB12nq_9Pg4_Z6ZdNNpy5bPcYhRP-X3WgAvFY2oiExs9_u_s4GH5czmjnJrSID6Ze77kC21G3_vDpMlP-ihHSqMgEUs0r-hjlo2ZHncvWmMByLRuXh4U7rQOrv0Hj9q8vRrJ69ov1_iz7uChWmvhkN8WFtvHoRAwIgMAfB_vKAF_Y-FHP__95ZXy5N2ASL-GTvOA" />
                </div>
              </div>

              {/* Auto-Notes */}
              <div className="border-hard bg-surface-container-lowest flex flex-col shadow-hard min-h-[200px] max-h-[300px] flex-1">
                <div className="border-b-[1.5px] border-primary p-sm bg-surface-container-lowest flex justify-between items-center shrink-0">
                  <span className="font-label-caps text-label-caps text-primary">AUTO-GENERATED NOTES</span>
                  <span className="material-symbols-outlined text-primary text-sm">edit_note</span>
                </div>
                <div className="p-md font-mono-body text-mono-body text-on-surface bg-surface-container-low flex-1 overflow-y-auto leading-relaxed">
                  <p className="text-secondary italic">Notes will appear here during the interview...</p>
                </div>
              </div>
            </div>
          </div>

          {/* Q&A Transcript Feed */}
          <section className={`border-hard bg-surface-container-lowest flex flex-col shadow-hard flex-1 min-h-[400px] transition-opacity ${!roomCode ? 'opacity-50 pointer-events-none' : ''}`}>
            <div className="p-sm border-b-[1.5px] border-primary flex justify-between items-center bg-surface-container-lowest sticky top-0 z-10 shrink-0">
              <span className="font-label-caps text-label-caps text-primary">LIVE TRANSCRIPT</span>
              <span className="material-symbols-outlined text-primary text-sm">forum</span>
            </div>
            <div className="p-md flex-1 overflow-y-auto space-y-md bg-surface flex flex-col items-center justify-center">
              <p className="text-secondary font-mono-body">Awaiting conversation...</p>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
