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
