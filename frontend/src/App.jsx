import { Routes, Route } from "react-router-dom"
import Transcript from "./pages/Transcript"
import BottomDock from "./components/bottom-dock"
import Monitor from "./pages/Monitor"

function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<Monitor />} />
        <Route path="/transcript" element={<Transcript />} />
      </Routes>
      <BottomDock />
    </>
  )
}

export default App
