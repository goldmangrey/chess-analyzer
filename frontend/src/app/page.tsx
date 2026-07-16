export default function Home() {
  return (
    <main className="flex min-h-screen items-center justify-center px-6 py-16">
      <section className="w-full max-w-xl rounded-2xl border border-zinc-200 bg-white p-8 shadow-sm">
        <p className="text-sm font-medium uppercase tracking-widest text-emerald-700">
          Foundation
        </p>
        <h1 className="mt-3 text-4xl font-semibold tracking-tight text-zinc-950">
          Chess AI Teacher
        </h1>
        <p className="mt-4 text-lg leading-8 text-zinc-600">
          Локальный фундамент проекта запущен.
        </p>
        <dl className="mt-8 space-y-3 border-t border-zinc-200 pt-6 text-sm">
          <div className="flex items-center justify-between gap-4">
            <dt className="text-zinc-500">Frontend</dt>
            <dd className="font-medium text-emerald-700">работает</dd>
          </div>
          <div className="flex items-center justify-between gap-4">
            <dt className="text-zinc-500">Backend health</dt>
            <dd>
              <a
                className="font-mono text-zinc-800 underline decoration-zinc-300 underline-offset-4 hover:decoration-zinc-700"
                href="http://127.0.0.1:8000/health"
              >
                GET /health
              </a>
            </dd>
          </div>
        </dl>
      </section>
    </main>
  );
}
