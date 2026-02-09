export default function JobCard({ job }) {
    const statusColors = {
        queued: "bg-gray-100 border-gray-300 text-gray-600",
        running: "bg-blue-50 border-blue-300 text-blue-700 animate-pulse",
        completed: "bg-green-50 border-green-300 text-green-700",
        error: "bg-red-50 border-red-300 text-red-700",
    };

    const currentStyle = statusColors[job.status] || statusColors.queued;

    const duration = (job.end && job.start)
        ? (job.end - job.start).toFixed(2) + "s"
        : "-";

    return (
        <div className={`p-4 rounded-lg border-l-4 shadow-sm mb-3 transition-all ${currentStyle}`}>
            <div className="flex justify-between items-start">
                <div>
                    <h3 className="font-bold text-lg">{job.name}</h3>
                    <p className="text-xs uppercase tracking-wide opacity-75">
                        {job.type} • {job.id.slice(0, 8)}
                    </p>
                </div>
                <span className="px-2 py-1 rounded text-xs font-bold uppercase bg-white/50 border border-current">
                    {job.status}
                </span>
            </div>

            <div className="mt-4 grid grid-cols-2 gap-4 text-sm opacity-80">
                <div>
                    <span className="block text-xs uppercase opacity-60">Started</span>
                    {job.start ? new Date(job.start * 1000).toLocaleTimeString() : "-"}
                </div>
                <div>
                    <span className="block text-xs uppercase opacity-60">Duration</span>
                    {duration}
                </div>
            </div>

            {job.error && (
                <div className="mt-3 p-2 bg-red-100 text-red-800 text-xs rounded font-mono break-all">
                    Error: {job.error}
                </div>
            )}
        </div>
    );
}