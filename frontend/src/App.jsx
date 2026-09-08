import { useState } from 'react';
import UploadPage from './pages/UploadPage.jsx';
import ViewerPage from './pages/ViewerPage.jsx';
import './index.css';

export default function App() {
  const [uploadInfo, setUploadInfo] = useState(null);

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {uploadInfo ? (
        <ViewerPage
          uploadInfo={uploadInfo}
          onBack={() => setUploadInfo(null)}
        />
      ) : (
        <UploadPage onUploaded={setUploadInfo} />
      )}
    </div>
  );
}
