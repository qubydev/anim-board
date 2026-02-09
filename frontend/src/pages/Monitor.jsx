import useJobs from "../hooks/useJobs";
import JobCard from "../components/JobCard";

export default function Monitor() {
  const jobs = useJobs();

  const sortedJobs = [...jobs].sort((a, b) => {
    return new Date(b.created_at || 0) - new Date(a.created_at || 0);
  });

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800">System Monitor</h1>
        <span className="text-sm text-gray-500">
          {jobs.length} Job{jobs.length !== 1 && "s"} Found
        </span>
      </div>

      {jobs.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg border border-dashed border-gray-300">
          <p className="text-gray-500">No active jobs.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {sortedJobs.map((job) => (
            <JobCard key={job.id} job={job} />
          ))}
        </div>
      )}
    </div>
  );
}