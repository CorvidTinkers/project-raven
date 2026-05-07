'use client';

import React from 'react';
import { Award, Sparkles, CheckCircle, TrendingUp, Download } from 'lucide-react';
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis,
  PolarRadiusAxis, ResponsiveContainer,
} from 'recharts';

interface ReportViewProps {
  grade: any;
}

export default function ReportView({ grade }: ReportViewProps) {
  // If no grade, show a clean "not available" state
  if (!grade) {
    return (
      <div className="flex flex-col items-center gap-6 py-24 text-center animate-in fade-in duration-700">
        <Award size={48} className="text-slate-600" />
        <div className="space-y-2">
          <p className="text-xl font-black text-white">Interview Complete</p>
          <p className="text-slate-500 text-sm">No code submission was recorded for this session.</p>
        </div>
      </div>
    );
  }

  const scores = grade.scores || {};
  const feedback = grade.feedback || {};

  const chartData = [
    { subject: 'Correctness', A: (scores.correctness ?? 0) * 10, fullMark: 100 },
    { subject: 'Complexity',  A: (scores.complexity  ?? 0) * 10, fullMark: 100 },
    { subject: 'Clarity',     A: (scores.clarity     ?? 0) * 10, fullMark: 100 },
    { subject: 'Edge Cases',  A: (scores.edge_cases  ?? 0) * 10, fullMark: 100 },
  ];

  const handleDownload = () => {
    const blob = new Blob([JSON.stringify(grade, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'raven-report.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col items-center gap-10 w-full animate-in fade-in slide-in-from-bottom-8 duration-1000">
      {/* Score header */}
      <div className="flex flex-col items-center text-center gap-4">
        <div className="p-4 bg-yellow-500/10 rounded-full border border-yellow-500/20 text-yellow-500 animate-pulse">
          <Award size={48} />
        </div>
        <h2 className="text-4xl font-black text-white tracking-tighter uppercase">Evaluation Complete</h2>
        <div className="relative group">
          <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg blur opacity-25 group-hover:opacity-50 transition duration-700" />
          <div className="relative px-8 py-4 bg-slate-900 rounded-lg border border-slate-700 flex items-center">
            <span className="text-5xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-400">
              {grade.grade ?? '—'}/10
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 w-full">
        {/* Radar chart */}
        <div className="bg-slate-800/40 border border-slate-700/50 p-6 rounded-3xl h-[320px] flex flex-col">
          <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4 flex items-center gap-2">
            <Sparkles size={14} /> Performance Breakdown
          </h3>
          <div className="flex-1 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart cx="50%" cy="50%" outerRadius="75%" data={chartData}>
                <PolarGrid stroke="#334155" />
                <PolarAngleAxis dataKey="subject" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                <Radar
                  name="Score"
                  dataKey="A"
                  stroke="#3b82f6"
                  fill="#3b82f6"
                  fillOpacity={0.35}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Textual feedback */}
        <div className="flex flex-col gap-4">
          {feedback.summary && (
            <div className="bg-blue-600/5 border border-blue-500/20 p-6 rounded-3xl">
              <h3 className="font-black text-blue-400 mb-3 flex items-center gap-2 uppercase tracking-tighter text-sm">
                <CheckCircle size={16} /> Executive Feedback
              </h3>
              <p className="text-slate-300 leading-relaxed text-sm italic">
                "{feedback.summary}"
              </p>
            </div>
          )}

          {feedback.strengths?.length > 0 && (
            <div className="bg-green-600/5 border border-green-500/20 p-5 rounded-3xl">
              <h4 className="text-[10px] font-black text-green-500 uppercase tracking-widest mb-2 flex items-center gap-2">
                <TrendingUp size={12} /> Strengths
              </h4>
              <ul className="space-y-1">
                {feedback.strengths.map((s: string, i: number) => (
                  <li key={i} className="text-slate-300 text-xs flex items-start gap-2">
                    <span className="text-green-500 mt-0.5">✓</span> {s}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {feedback.weaknesses?.length > 0 && (
            <div className="bg-red-600/5 border border-red-500/20 p-5 rounded-3xl">
              <h4 className="text-[10px] font-black text-red-500 uppercase tracking-widest mb-2">
                Areas to Improve
              </h4>
              <ul className="space-y-1">
                {feedback.weaknesses.map((w: string, i: number) => (
                  <li key={i} className="text-slate-300 text-xs flex items-start gap-2">
                    <span className="text-red-500 mt-0.5">→</span> {w}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      <button
        onClick={handleDownload}
        className="flex items-center gap-3 px-8 py-4 bg-slate-800/50 border border-slate-700 hover:border-blue-500 hover:text-blue-400 rounded-2xl text-slate-400 text-sm font-bold transition-all"
      >
        <Download size={16} /> Download Report (JSON)
      </button>
    </div>
  );
}
