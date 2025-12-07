import React, { createContext, useContext, useState, useEffect } from 'react';

const ApproachContext = createContext();

export const useApproach = () => {
  const context = useContext(ApproachContext);
  if (!context) {
    throw new Error('useApproach must be used within an ApproachProvider');
  }
  return context;
};

export const APPROACHES = {
  hybrid: {
    id: 'hybrid',
    name: 'Hybrid Search',
    description: 'BM25 + Vector search on structured university profiles',
    icon: '🎯',
    features: [
      'Structured university profiles',
      'BM25 + Vector hybrid search',
      'Admissions, outcomes, strategy data',
      'Fast semantic search'
    ],
    bestFor: 'Comprehensive college research and analysis'
  },
  rag: {
    id: 'rag',
    name: 'RAG (File Search)',
    description: 'Google Vertex AI RAG - Fully managed, easy to use',
    icon: '📚',
    features: [
      'Fully managed service',
      'Built-in chunking',
      'Easy setup',
      'Vertex AI powered'
    ],
    bestFor: 'Simple deployments and quick setup'
  },
  elasticsearch: {
    id: 'elasticsearch',
    name: 'Elasticsearch',
    description: 'Advanced search with custom scoring and filters',
    icon: '🔍',
    features: [
      'Powerful full-text search',
      'Custom relevance scoring',
      'Flexible queries',
      'Advanced filters'
    ],
    bestFor: 'Advanced search features and full control'
  },
  vertexai: {
    id: 'vertexai',
    name: 'Vertex AI',
    description: 'ADK RAG with Vertex AI corpora - Advanced semantic search',
    icon: '🧠',
    features: [
      'Vertex AI RAG Engine',
      'Semantic search',
      'Agent-based uploads',
      'User-scoped corpora'
    ],
    bestFor: 'Advanced RAG with semantic understanding'
  }
};

export const ApproachProvider = ({ children }) => {
  const [selectedApproach, setSelectedApproach] = useState('rag');
  const [isApproachSelected, setIsApproachSelected] = useState(false);

  // Load saved approach from localStorage on mount
  useEffect(() => {
    const savedApproach = localStorage.getItem('knowledgeBaseApproach');
    const approachSelected = localStorage.getItem('approachSelected');

    if (savedApproach && APPROACHES[savedApproach]) {
      setSelectedApproach(savedApproach);
    }

    if (approachSelected === 'true') {
      setIsApproachSelected(true);
    }
  }, []);

  const selectApproach = (approach) => {
    if (APPROACHES[approach]) {
      setSelectedApproach(approach);
      setIsApproachSelected(true);
      localStorage.setItem('knowledgeBaseApproach', approach);
      localStorage.setItem('approachSelected', 'true');
      console.log(`[APPROACH] Selected: ${approach}`);
    } else {
      console.error(`[APPROACH] Invalid approach: ${approach}`);
    }
  };

  const resetApproachSelection = () => {
    setIsApproachSelected(false);
    localStorage.setItem('approachSelected', 'false');
  };

  const getApproachInfo = () => {
    return APPROACHES[selectedApproach] || APPROACHES.rag;
  };

  const value = {
    selectedApproach,
    selectApproach,
    isApproachSelected,
    resetApproachSelection,
    getApproachInfo,
    allApproaches: APPROACHES
  };

  return (
    <ApproachContext.Provider value={value}>
      {children}
    </ApproachContext.Provider>
  );
};
