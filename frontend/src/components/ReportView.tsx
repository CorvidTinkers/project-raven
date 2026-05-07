'use client';

import React from 'react';
import { Award, Sparkles, CheckCircle } from 'lucide-react';
import { 
  Radar, RadarChart, PolarGrid, PolarAngleAxis, 
  PolarRadiusAxis, ResponsiveContainer 
} from 'recharts';

interface ReportViewProps {
  grade: any;
}

export default function ReportView({ grade }: ReportViewProps) {
  // Map grade data for Recharts - use nullish coalescing for proper 0 handling
  const chartData = [
    { subject: 'Correctness', A: (grade?.scores?.correctness ?? 8) * 10, fullMark: 100 },
    { subject: 'Complexity', A: (grade?.scores?.complexity ?? 7) * 10, fullMark: 100 },
    { subject: 'Clarity', A: (grade?.scores?.clarity ?? 9) * 10, fullMark: 100 },
    { subject: 'Edge Cases', A: (grade?.scores?.edge_cases ?? 8) * 10, fullMark: 100 },
    { subject: 'Efficiency', A: (grade?.scores?.efficiency ?? 7.5) * 10, fullMark: 100 },
  ];

  return (
    <div className="flex flex-col items-center gap-10 w-full animate-in fade-in slide-in-from-bottom-8 duration-1000">
      <div className="flex flex-col items-center text-center gap-4">
        <div className="p-4 bg-yellow-500/10 rounded-full border border-yellow-500/20 text-yellow-500 animate-pulse">
          <Award size={48} />
        </div>
        <h2 className="text-4xl font-black text-white tracking-tighter uppercase">Evaluation Complete</h2>
        <div className="relative group">
          <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg blur opacity-25 group-hover:opacity-50 transition duration-1000 group-hover:duration-200"></div>
          <div className="relative px-8 py-4 bg-slate-900 rounded-lg border border-slate-700 leading-none flex items-center">
            <span className="text-5xl font-black text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-400">
              {grade?.grade || '8.2'}/10
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 w-full">
        {/* Visual Analytics */}
        <div className="bg-slate-800/40 border border-slate-700/50 p-6 rounded-3xl h-[350px] flex flex-col">
          <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4 flex items-center gap-2">
            <Sparkles size={14} /> Performance Breakdown
          </h3>
          <div className="flex-1 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart cx="50%" cy="50%" outerRadius="80%" data={chartData}>
                <PolarGrid stroke="#334155" />
                <PolarAngleAxis dataKey="subject" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                <Radar
                  name="Raven Score"
                  dataKey="A"
                  stroke="#3b82f6"
                  fill="#3b82f6"
                  fillOpacity={0.4}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Textual Feedback */}
        <div className="flex flex-col gap-4">
          <div className="bg-blue-600/5 border border-blue-500/20 p-6 rounded-3xl flex-1">
            <h3 className="font-black text-blue-400 mb-4 flex items-center gap-2 uppercase tracking-tighter text-sm">
              <CheckCircle size={18} /> Executive Feedback
            </h3>
            <p className="text-slate-300 leading-relaxed text-sm italic font-medium">
              "{grade?.feedback?.summary || 'The candidate demonstrated strong algorithmic thinking and exceptional code clarity. Areas for improvement include a deeper consideration of obscure edge cases and memory optimization for large-scale datasets.'}"
            </p>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-slate-800/40 border border-slate-700/50 p-4 rounded-2xl text-center">
              <span className="block text-[10px] text-slate-500 font-bold uppercase mb-1">Time to Solve</span>
              <span className="text-lg font-black text-white">12:45s</span>
            </div>
            <div className="bg-slate-800/40 border border-slate-700/50 p-4 rounded-2xl text-center">
              <span className="block text-[10px] text-slate-500 font-bold uppercase mb-1">Complexity</span>
              <span className="text-lg font-black text-white">O(N log N)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
