export function CalendarCard() {
  const days = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];
  const dates = Array.from({ length: 28 }).map((_, index) => index + 3);

  return (
    <div className="rounded-3xl border border-slate-800 bg-slate-900/90 p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.35em] text-slate-400">Calendar</p>
          <h3 className="mt-2 text-lg font-semibold text-white">Team availability</h3>
        </div>
        <button className="rounded-full border border-slate-700 px-3 py-2 text-sm text-slate-300 hover:border-cyan-400">View</button>
      </div>
      <div className="mt-6 grid grid-cols-7 gap-2 text-center text-xs text-slate-500">
        {days.map((day, index) => (
          <span key={`${day}-${index}`} className="font-semibold text-slate-400">{day}</span>
        ))}
      </div>
      <div className="mt-3 grid grid-cols-7 gap-2 text-sm text-slate-100">
        {dates.map((date) => (
          <div key={date} className="rounded-2xl border border-slate-800 bg-slate-950/90 px-2 py-3">{date}</div>
        ))}
      </div>
    </div>
  );
}
