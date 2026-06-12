'use client';

import React, { useState, useEffect } from 'react';
import { 
  Library, 
  Plus, 
  Folder, 
  FileText, 
  Upload, 
  CheckCircle, 
  Loader, 
  AlertCircle,
  Search,
  BookOpen
} from 'lucide-react';
import { api } from '../../../lib/api';

interface Collection {
  id: string;
  name: string;
  description?: string;
  created_at: string;
}

interface DocumentRecord {
  id: string;
  name: string;
  file_type: string;
  size_bytes: number;
  status: string;
  error_message?: string;
  created_at: string;
}

export default function KnowledgePage() {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [selectedCol, setSelectedCol] = useState<Collection | null>(null);
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');
  
  // File upload state
  const [uploading, setUploading] = useState(false);
  const [uploadErr, setUploadErr] = useState('');

  // Semantic query test state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    fetchCollections();
  }, []);

  useEffect(() => {
    if (selectedCol) {
      fetchDocuments(selectedCol.id);
    } else {
      setDocuments([]);
    }
  }, [selectedCol]);

  const fetchCollections = async () => {
    try {
      const res = await api.get('/knowledge/collections');
      setCollections(res);
      if (res.length > 0 && !selectedCol) {
        setSelectedCol(res[0]);
      }
    } catch (err) {
      console.error('Error fetching collections:', err);
    }
  };

  const fetchDocuments = async (colId: string) => {
    try {
      const res = await api.get(`/knowledge/collections/${colId}/documents`);
      setDocuments(res);
    } catch (err) {
      console.error('Error fetching documents:', err);
    }
  };

  const handleCreateCollection = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;

    try {
      const newCol = await api.post('/knowledge/collections', {
        name: newName.trim(),
        description: newDesc.trim()
      });
      setCollections((prev) => [...prev, newCol]);
      setSelectedCol(newCol);
      setNewName('');
      setNewDesc('');
      setShowCreateModal(false);
    } catch (err) {
      console.error(err);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!selectedCol || !e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    
    setUploading(true);
    setUploadErr('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      await api.post(`/knowledge/collections/${selectedCol.id}/upload`, formData);
      fetchDocuments(selectedCol.id);
    } catch (err: any) {
      setUploadErr(err.message || 'File upload failed.');
    } finally {
      setUploading(false);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCol || !searchQuery.trim()) return;

    setSearching(true);
    try {
      const formData = new FormData();
      formData.append('query', searchQuery);
      formData.append('limit', '3');
      const res = await api.post(`/knowledge/collections/${selectedCol.id}/query`, formData);
      setSearchResults(res.results || []);
    } catch (err) {
      console.error(err);
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="flex-1 bg-black p-6 md:p-8 overflow-y-auto max-h-screen">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white mb-2 flex items-center gap-3">
            <Library className="text-violet-500" /> Knowledge Base
          </h1>
          <p className="text-sm text-zinc-400">
            Ingest local files, process text overlaps, and index embeddings inside ChromaDB.
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-violet-600 to-indigo-600 hover:brightness-110 text-white text-sm font-semibold rounded-lg transition"
        >
          <Plus size={16} /> New Collection
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Collections List Pane */}
        <div className="lg:col-span-1 space-y-3">
          <h2 className="text-xs font-bold text-zinc-500 uppercase tracking-wider px-2">Collections</h2>
          <div className="space-y-1">
            {collections.map((col) => {
              const isSelected = selectedCol?.id === col.id;
              return (
                <button
                  key={col.id}
                  onClick={() => setSelectedCol(col)}
                  className={`
                    w-full text-left flex items-center gap-3 px-3 py-3 rounded-lg text-sm transition
                    ${isSelected 
                      ? 'bg-zinc-900 border border-zinc-850 text-white' 
                      : 'text-zinc-450 hover:bg-zinc-950 hover:text-zinc-200 border border-transparent'}
                  `}
                >
                  <Folder size={16} className={isSelected ? 'text-violet-400' : 'text-zinc-500'} />
                  <span className="truncate font-medium">{col.name}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Collection details and uploader */}
        <div className="lg:col-span-3 space-y-6">
          {selectedCol ? (
            <>
              {/* Stats overview */}
              <div className="p-6 rounded-xl bg-zinc-950 border border-zinc-850/60 space-y-4">
                <h3 className="text-xl font-bold text-white">{selectedCol.name}</h3>
                <p className="text-zinc-400 text-sm">{selectedCol.description || 'No description provided.'}</p>

                {/* Upload Document Box */}
                <div className="pt-4 border-t border-zinc-850">
                  <label className="flex flex-col items-center justify-center p-6 border-2 border-dashed border-zinc-800 rounded-xl cursor-pointer hover:border-violet-600 transition">
                    {uploading ? (
                      <Loader className="w-8 h-8 text-violet-500 animate-spin mb-3" />
                    ) : (
                      <Upload className="w-8 h-8 text-zinc-500 mb-3" />
                    )}
                    <span className="text-sm font-semibold text-zinc-300">
                      {uploading ? 'Ingesting document...' : 'Click to Upload PDF, Markdown, or text'}
                    </span>
                    <input 
                      type="file" 
                      onChange={handleFileUpload} 
                      className="hidden" 
                      disabled={uploading}
                    />
                  </label>
                  {uploadErr && (
                    <p className="text-xs text-rose-400 mt-2 flex items-center gap-1.5"><AlertCircle size={14} /> {uploadErr}</p>
                  )}
                </div>
              </div>

              {/* Ingested Documents List */}
              <div className="glass-panel p-6 rounded-xl border border-zinc-800/60">
                <h3 className="text-lg font-bold text-zinc-200 mb-4 flex items-center gap-2"><BookOpen size={18} /> Ingested Documents ({documents.length})</h3>
                
                {documents.length === 0 ? (
                  <div className="text-center py-10 text-zinc-500 text-sm">
                    No documents ingested yet in this collection.
                  </div>
                ) : (
                  <div className="divide-y divide-zinc-850">
                    {documents.map((doc) => (
                      <div key={doc.id} className="py-3 flex items-center justify-between gap-4">
                        <div className="flex items-center gap-3 min-w-0">
                          <FileText size={16} className="text-violet-400 shrink-0" />
                          <div className="min-w-0">
                            <h4 className="text-sm font-semibold text-zinc-300 truncate">{doc.name}</h4>
                            <p className="text-xs text-zinc-500 mt-0.5">Size: {(doc.size_bytes / 1024).toFixed(1)} KB • Type: {doc.file_type.toUpperCase()}</p>
                          </div>
                        </div>

                        <div>
                          {doc.status === 'completed' && (
                            <span className="flex items-center gap-1.5 text-xs text-emerald-400 font-semibold bg-emerald-950/20 border border-emerald-900/40 rounded-full px-2.5 py-1">
                              <CheckCircle size={12} /> Complete
                            </span>
                          )}
                          {doc.status === 'processing' && (
                            <span className="flex items-center gap-1.5 text-xs text-zinc-400 font-semibold bg-zinc-900 border border-zinc-800 rounded-full px-2.5 py-1">
                              <Loader size={12} className="animate-spin" /> Ingesting
                            </span>
                          )}
                          {doc.status === 'failed' && (
                            <span className="flex items-center gap-1.5 text-xs text-rose-400 font-semibold bg-rose-950/20 border border-rose-900/40 rounded-full px-2.5 py-1" title={doc.error_message}>
                              <AlertCircle size={12} /> Failed
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Semantic Query Testing Window */}
              <div className="glass-panel p-6 rounded-xl border border-zinc-800/60">
                <h3 className="text-lg font-bold text-zinc-200 mb-4 flex items-center gap-2"><Search size={18} /> Test Semantic Search</h3>
                <form onSubmit={handleSearch} className="flex gap-3 mb-6">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Enter query search phrase..."
                    className="flex-1 bg-zinc-950 border border-zinc-850 rounded-xl px-4 py-2.5 text-sm text-zinc-200 focus:outline-none focus:border-violet-650"
                  />
                  <button
                    type="submit"
                    disabled={searching || !searchQuery.trim()}
                    className="px-5 py-2.5 bg-gradient-to-r from-violet-600 to-indigo-600 text-white font-semibold rounded-xl text-sm transition hover:brightness-110 disabled:opacity-50"
                  >
                    Query Vector
                  </button>
                </form>

                {searchResults.length > 0 && (
                  <div className="space-y-4">
                    {searchResults.map((res, index) => (
                      <div key={index} className="p-4 rounded-lg bg-zinc-950 border border-zinc-850/60">
                        <div className="flex justify-between items-center text-xs text-zinc-500 mb-2">
                          <span>Chunk Index: {res.chunk_index}</span>
                          <span>Score: {res.score.toFixed(4)}</span>
                        </div>
                        <p className="text-sm text-zinc-300 whitespace-pre-wrap">"{res.content}"</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="h-64 flex flex-col items-center justify-center border border-dashed border-zinc-800 rounded-xl text-zinc-500">
              Create a collection to start uploading documents.
            </div>
          )}
        </div>
      </div>

      {/* Modal Dialog */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <form onSubmit={handleCreateCollection} className="w-full max-w-md bg-zinc-950 border border-zinc-800 rounded-xl p-6 space-y-4 shadow-xl">
            <h3 className="text-xl font-bold text-white">Create Knowledge Collection</h3>
            
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-zinc-400">Collection Name</label>
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="e.g., Customer Support FAQs"
                className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3.5 py-2 text-sm text-zinc-200 focus:outline-none focus:border-violet-650"
                required
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-zinc-400">Description</label>
              <textarea
                value={newDesc}
                onChange={(e) => setNewDesc(e.target.value)}
                placeholder="Brief summary of contents..."
                className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3.5 py-2 text-sm text-zinc-200 focus:outline-none focus:border-violet-650 h-24"
              />
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 bg-zinc-900 text-zinc-300 hover:text-white rounded-lg text-sm transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-gradient-to-r from-violet-600 to-indigo-600 text-white font-semibold rounded-lg text-sm transition hover:brightness-110"
              >
                Create
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
