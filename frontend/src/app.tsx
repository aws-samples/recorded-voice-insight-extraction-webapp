import {
  HashRouter,
  BrowserRouter,
  Routes,
  Route,
} from "react-router-dom";
import { USE_BROWSER_ROUTER } from "./common/constants";
import GlobalHeader from "./components/global-header";
import HomePage from "./pages/Home";
import FileManagementPage from "./pages/FileManagement";
import FileUploadPage from "./pages/FileUpload";
import JobStatus from "./pages/JobStatus";
import Analyze from "./pages/Analyze";
import ChatWithMediaPage from "./pages/ChatWithMedia";
import NotFound from "./pages/not-found";
import "./styles/app.scss";

export default function App() {
  const Router = USE_BROWSER_ROUTER ? BrowserRouter : HashRouter;

  return (
    <div style={{ height: "100%" }}>
      <Router>
        <GlobalHeader />
        <div style={{ height: "56px", backgroundColor: "#000716" }}>&nbsp;</div>
        <div>
          <Routes>
            <Route index path="/" element={<HomePage />} />
            <Route path="/home" element={<HomePage />} />
            <Route path="/file-management" element={<FileManagementPage />} />
            <Route path="/file-upload" element={<FileUploadPage />} />
            <Route path="/job-status" element={<JobStatus />} />
            <Route path="/analyze" element={<Analyze />} />
            <Route path="/chat-with-media" element={<ChatWithMediaPage />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </div>
      </Router>
    </div>
  );
}
