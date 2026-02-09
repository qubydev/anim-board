import { useState } from "react"
import { Button } from "@/components/ui/button"
import { useJobs } from "@/hooks/useJobs"
import toast from "react-hot-toast"

const API = import.meta.env.VITE_BACKEND_URL

export default function Transcript() {
  const [file, setFile] = useState(null)
  const { isJobRunning } = useJobs()
  const transcriptionRunning = isJobRunning("transcription")

  const uploadAndTranscribe = async () => {
    if (!file) return
    const fd = new FormData()
    fd.append("file", file)

    try {
      const upload = await fetch(`${API}/api/upload-audio`, {
        method: "POST",
        body: fd
      }).then(r => r.json())

      await fetch(`${API}/api/transcribe`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: upload.path })
      })

      toast.success("Transcription started")
      setFile(null)
    } catch (err) {
      console.error(err)
      toast.error("Failed to start transcription")
    }
  }

  return (
    <div className="p-6 space-y-4">
      <input
        type="file"
        accept="audio/*"
        onChange={e => setFile(e.target.files[0])}
      />

      <Button
        onClick={uploadAndTranscribe}
        disabled={transcriptionRunning}
      >
        {transcriptionRunning ? "Transcription running…" : "Start Transcription"}
      </Button>
    </div>
  )
}
