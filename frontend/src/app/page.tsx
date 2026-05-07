import Link from 'next/link';

export default function LandingPage() {
  return (
    <div className="flex flex-col h-screen overflow-hidden bg-surface">
      <header className="bg-surface text-primary font-h2 text-h2 w-full top-0 border-b-[1.5px] border-primary flex justify-between items-center px-md py-sm shrink-0 z-20">
        <div className="flex items-center gap-sm">
          <div className="w-8 h-8 bg-primary text-on-primary flex items-center justify-center font-bold text-body">R</div>
          <div className="font-h1 text-h1 font-bold text-primary">Project Raven</div>
        </div>
        <div className="font-label-caps text-label-caps flex items-center gap-xs">
          <span className="w-2 h-2 rounded-full bg-primary block"></span>
          System: Operational
        </div>
      </header>
      
      <main className="flex-1 flex items-center justify-center p-gutter relative z-10">
        <div className="border-hard bg-surface-container-lowest p-xl flex flex-col shadow-hard items-center max-w-lg w-full gap-lg">
          <div className="flex flex-col items-center gap-xs">
            <h2 className="font-h1 text-h1 text-primary font-bold text-center">Welcome</h2>
            <p className="font-body text-body text-secondary text-center">Select your portal to continue.</p>
          </div>
          
          <div className="flex flex-col gap-md w-full mt-sm">
            <Link 
              href="/candidate"
              className="border-hard bg-primary text-on-primary p-md shadow-hard-hover flex items-center justify-center font-label-caps text-label-caps transition-all"
            >
              Enter Candidate View
            </Link>
            
            <Link 
              href="/admin"
              className="border-hard bg-surface-container-high text-primary p-md shadow-hard-hover flex items-center justify-center font-label-caps text-label-caps transition-all"
            >
              Enter Admin Dashboard
            </Link>
            
            <Link 
              href="/legacy"
              className="text-secondary hover:text-primary p-sm flex items-center justify-center font-mono-body text-mono-body transition-all mt-xs"
            >
              Access Legacy Endpoint
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
