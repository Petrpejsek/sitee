export default function LockOverlay({ onUnlock }) {
  return (
    <div className="relative min-h-[400px]">
      {/* Blurred placeholder content */}
      <div className="pointer-events-none select-none blur-[8px] filter">
        <div className="space-y-4">
          <div className="h-8 w-3/4 rounded bg-gray-200"></div>
          <div className="h-4 w-full rounded bg-gray-100"></div>
          <div className="h-4 w-5/6 rounded bg-gray-100"></div>
          <div className="h-4 w-4/5 rounded bg-gray-100"></div>
          <div className="mt-6 space-y-3">
            <div className="h-32 w-full rounded-lg bg-gray-200"></div>
            <div className="h-32 w-full rounded-lg bg-gray-200"></div>
          </div>
        </div>
      </div>

      {/* Minimal popup */}
      <div className="absolute inset-0 flex items-center justify-center bg-gray-900/30 backdrop-blur-md">
        <div className="mx-4 w-full max-w-md rounded-3xl border-2 border-gray-300 bg-white px-12 py-12 shadow-[0_20px_60px_rgba(0,0,0,0.15)]">
          
          {/* Headline */}
          <h1 className="mb-3 text-center text-3xl font-extrabold leading-tight tracking-tight text-gray-900">
            Your company is <span className="text-transparent bg-clip-text bg-gradient-to-r from-red-600 to-orange-600">invisible</span> for GPT, Gemini, Perplexity etc.
          </h1>

          {/* Subline */}
          <p className="mb-10 text-center text-xl font-medium text-gray-700">
            AI sends traffic to <span className="font-bold text-blue-600">others.</span>
          </p>

          {/* CTA */}
          <button
            onClick={onUnlock}
            className="w-full rounded-xl bg-gradient-to-r from-blue-600 to-blue-700 px-8 py-5 text-xl font-bold text-white shadow-lg transition-all hover:from-blue-700 hover:to-blue-800 hover:shadow-xl active:scale-[0.97]"
          >
            Get AI traffic now
          </button>

        </div>
      </div>
    </div>
  )
}
