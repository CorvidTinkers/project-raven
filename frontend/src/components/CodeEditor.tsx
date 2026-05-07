'use client';

import React, { useState, useCallback } from 'react';
import Editor from '@monaco-editor/react';
import { Send, CheckCircle } from 'lucide-react';

interface CodeEditorProps {
  language: 'python' | 'javascript' | 'sql' | 'java';
  defaultCode?: string;
  onSubmit?: (code: string) => void;
  readOnly?: boolean;
}

export default function CodeEditor({ 
  language = 'python', 
  defaultCode = '',
  onSubmit,
  readOnly = false 
}: CodeEditorProps) {
  const [code, setCode] = useState(defaultCode);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const handleEditorChange = useCallback((value: string | undefined) => {
    setCode(value || '');
    setIsSubmitted(false);
  }, []);

  const handleSubmit = useCallback(() => {
    if (onSubmit) {
      onSubmit(code);
      setIsSubmitted(true);
    }
  }, [code, onSubmit]);

  return (
    <div className="flex flex-col h-full w-full bg-[#1e1e1e] rounded-xl overflow-hidden border border-slate-700 shadow-2xl">
      <div className="flex items-center justify-between px-4 py-2 bg-[#252526] border-b border-slate-700">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-red-500" />
          <div className="w-3 h-3 rounded-full bg-yellow-500" />
          <div className="w-3 h-3 rounded-full bg-green-500" />
          <span className="ml-2 text-xs font-mono text-slate-400 uppercase tracking-wider">
            {language} editor
          </span>
        </div>
        {!readOnly && (
          <button
            onClick={handleSubmit}
            disabled={isSubmitted}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-md text-sm font-semibold transition-all ${
              isSubmitted 
                ? 'bg-green-600/20 text-green-400 cursor-default' 
                : 'bg-blue-600 hover:bg-blue-700 text-white shadow-lg active:scale-95'
            }`}
          >
            {isSubmitted ? (
              <><CheckCircle size={16} /> Submitted</>
            ) : (
              <><Send size={16} /> Submit Solution</>
            )}
          </button>
        )}
      </div>
      
      <div className="flex-1 min-h-[350px]">
        <Editor
          height="100%"
          language={language}
          value={code}
          onChange={handleEditorChange}
          theme="vs-dark"
          options={{
            minimap: { enabled: false },
            fontSize: 14,
            lineNumbers: 'on',
            scrollBeyondLastLine: false,
            readOnly: readOnly,
            automaticLayout: true,
            tabSize: 4,
            wordWrap: 'on',
            padding: { top: 16, bottom: 16 },
            fontFamily: "'Fira Code', 'Courier New', monospace",
          }}
        />
      </div>
      
      {isSubmitted && (
        <div className="px-4 py-2 bg-green-900/20 border-t border-green-900/30 text-green-400 text-xs font-mono">
          System: Solution captured. Raven is reviewing your code...
        </div>
      )}
    </div>
  );
}
