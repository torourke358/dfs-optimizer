import { useCallback, useRef, useState } from 'react';

interface Props {
  onFile: (file: File) => void;
  onLoadSample: () => void;
  loading: boolean;
}

export function UploadZone({ onFile, onLoadSample, loading }: Props) {
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) onFile(file);
    },
    [onFile],
  );

  return (
    <div className="upload-row">
      <div
        className={`dropzone${dragOver ? ' dropzone--over' : ''}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click();
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv,text/csv"
          hidden
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onFile(file);
            e.target.value = '';
          }}
        />
        <span className="dropzone__title">Drop a DraftKings salaries CSV</span>
        <span className="dropzone__sub">or click to browse</span>
      </div>
      <div className="upload-row__or">or</div>
      <button className="btn btn--ghost" onClick={onLoadSample} disabled={loading}>
        Load sample slate
      </button>
    </div>
  );
}
