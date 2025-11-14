import { useState, useEffect } from 'react';
import {
  AcademicCapIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  XCircleIcon,
  SparklesIcon
} from '@heroicons/react/24/outline';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { startSession, sendMessage, extractResponseText } from '../services/api';
import { useAuth } from '../context/AuthContext';

function Analysis() {
  const { currentUser } = useAuth();
  const [collegeName, setCollegeName] = useState('');
  const [intendedMajor, setIntendedMajor] = useState('');
  const [analyzing, setAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [error, setError] = useState(null);
  const [conversationHistory, setConversationHistory] = useState([]);

  // Load saved data from localStorage
  useEffect(() => {
    const savedCollege = localStorage.getItem('collegeName');
    const savedMajor = localStorage.getItem('intendedMajor');
    
    if (savedCollege) setCollegeName(savedCollege);
    if (savedMajor) setIntendedMajor(savedMajor);
  }, []);

  // Save data to localStorage
  useEffect(() => {
    if (collegeName) localStorage.setItem('collegeName', collegeName);
    if (intendedMajor) localStorage.setItem('intendedMajor', intendedMajor);
  }, [collegeName, intendedMajor]);

  // Clear state when user changes
  useEffect(() => {
    if (!currentUser) {
      setCollegeName('');
      setIntendedMajor('');
      setAnalysis(null);
      setConversationHistory([]);
      setError(null);
    }
  }, [currentUser]);

  const handleAnalyze = async () => {
    if (!collegeName.trim()) {
      setError('Please enter the college name');
      return;
    }

    if (!intendedMajor.trim()) {
      setError('Please enter your intended major');
      return;
    }

    setAnalyzing(true);
    setError(null);
    setAnalysis(null);

    try {
      // Construct the analysis request message
      const message = `I want to analyze my admissions chances for ${collegeName}. My intended major is ${intendedMajor}.`;

      // Use startSession - it will reuse existing session from localStorage or create new one
      console.log('Sending analysis request...');
      const response = await startSession(message, currentUser?.email);

      // Extract the response text
      const responseText = extractResponseText(response);
      console.log('Agent response:', responseText);

      // Add to conversation history
      setConversationHistory(prev => [
        ...prev,
        { role: 'user', content: message },
        { role: 'assistant', content: responseText }
      ]);

      setAnalysis(responseText);
    } catch (err) {
      console.error('Analysis error:', err);
      setError(
        err.response?.data?.message || 
        'Failed to analyze admissions chances. Please make sure you have uploaded your student profile and try again.'
      );
    } finally {
      setAnalyzing(false);
    }
  };

  const handleReset = () => {
    setCollegeName('');
    setIntendedMajor('');
    setAnalysis(null);
    setConversationHistory([]);
    setError(null);
    // Keep the session - just clear the form and results
    // Session will be reused for the next analysis
  };

  const handleSendFollowUp = async (followUpMessage) => {
    if (!followUpMessage.trim()) return;

    setAnalyzing(true);
    setError(null);

    try {
      // Use startSession which will reuse the existing session
      const response = await startSession(followUpMessage, currentUser?.email);
      const responseText = extractResponseText(response);

      // Add to conversation history
      setConversationHistory(prev => [
        ...prev,
        { role: 'user', content: followUpMessage },
        { role: 'assistant', content: responseText }
      ]);

      setAnalysis(responseText);
    } catch (err) {
      console.error('Follow-up error:', err);
      setError('Failed to send follow-up message. Please try again.');
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Admissions Analysis</h1>
        <p className="mt-2 text-gray-600">
          Enter your target college and intended major to get a comprehensive admissions analysis.
        </p>
      </div>

      {/* Input Form */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">College Information</h2>
        
        <div className="space-y-4">
          {/* College Name */}
          <div>
            <label htmlFor="college-name" className="block text-sm font-medium text-gray-700 mb-2">
              Target College/University *
            </label>
            <input
              id="college-name"
              type="text"
              value={collegeName}
              onChange={(e) => setCollegeName(e.target.value)}
              placeholder="e.g., University of Southern California, Stanford University"
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-primary focus:border-primary"
              disabled={analyzing}
            />
          </div>

          {/* Intended Major */}
          <div>
            <label htmlFor="intended-major" className="block text-sm font-medium text-gray-700 mb-2">
              Intended Major *
            </label>
            <input
              id="intended-major"
              type="text"
              value={intendedMajor}
              onChange={(e) => setIntendedMajor(e.target.value)}
              placeholder="e.g., Computer Science, Business Administration, Biology"
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-primary focus:border-primary"
              disabled={analyzing}
            />
          </div>

          {/* Action Buttons */}
          <div className="flex space-x-4">
            <button
              onClick={handleAnalyze}
              disabled={analyzing || !collegeName.trim() || !intendedMajor.trim()}
              className={`flex-1 flex items-center justify-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white ${
                analyzing || !collegeName.trim() || !intendedMajor.trim()
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-primary hover:bg-blue-700'
              } transition-colors`}
            >
              {analyzing ? (
                <>
                  <ArrowPathIcon className="h-5 w-5 mr-2 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <SparklesIcon className="h-5 w-5 mr-2" />
                  Analyze Admissions Chances
                </>
              )}
            </button>

            {analysis && (
              <button
                onClick={handleReset}
                disabled={analyzing}
                className="px-6 py-3 border border-gray-300 text-base font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 transition-colors"
              >
                New Analysis
              </button>
            )}
          </div>

          {/* Error Message */}
          {error && (
            <div className="p-4 rounded-md bg-red-50">
              <div className="flex">
                <XCircleIcon className="h-5 w-5 text-red-400" />
                <p className="ml-3 text-sm text-red-800">{error}</p>
              </div>
            </div>
          )}
        </div>

        {/* Important Note */}
        <div className="mt-6 p-4 bg-blue-50 rounded-md">
          <h3 className="text-sm font-medium text-blue-900 mb-2">Before You Analyze:</h3>
          <ul className="text-sm text-blue-800 space-y-1 list-disc list-inside">
            <li>Make sure you've uploaded your student profile in the "Student Profile" tab</li>
            <li>The analysis will take 1-2 minutes as the AI agent gathers comprehensive data</li>
            <li>You'll receive a detailed report with risk assessment and recommendations</li>
          </ul>
        </div>
      </div>

      {/* Analysis Results */}
      {analysis && (
        <div className="bg-white shadow rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900">Analysis Report</h2>
            <div className="flex items-center text-sm text-green-600">
              <CheckCircleIcon className="h-5 w-5 mr-1" />
              Analysis Complete
            </div>
          </div>

          {/* Markdown Content */}
          <div className="prose prose-blue max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {analysis}
            </ReactMarkdown>
          </div>

          {/* Follow-up Section */}
          <div className="mt-6 pt-6 border-t border-gray-200">
            <h3 className="text-sm font-medium text-gray-900 mb-3">Have questions about this analysis?</h3>
            
            {analyzing && (
              <div className="mb-3 flex items-center text-sm text-blue-600">
                <ArrowPathIcon className="h-4 w-4 mr-2 animate-spin" />
                Processing your question...
              </div>
            )}
            
            <FollowUpInput onSend={handleSendFollowUp} disabled={analyzing} />
          </div>
        </div>
      )}

      {/* Conversation History */}
      {conversationHistory.length > 1 && (
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Follow-up Conversation ({conversationHistory.length - 2} messages)
          </h2>
          
          {/* Scrollable container with max height */}
          <div className="max-h-96 overflow-y-auto space-y-3 pr-2">
            {conversationHistory.slice(0, -2).map((message, index) => (
              <div
                key={index}
                className={`p-3 rounded-lg border ${
                  message.role === 'user'
                    ? 'bg-blue-50 border-blue-200 ml-12'
                    : 'bg-gray-50 border-gray-200 mr-12'
                }`}
              >
                <div className="flex items-center mb-2">
                  <p className="text-xs font-semibold text-gray-600">
                    {message.role === 'user' ? '👤 You' : '🤖 AI Counselor'}
                  </p>
                </div>
                <div className={`text-sm ${message.role === 'user' ? 'text-gray-800' : 'text-gray-900'}`}>
                  {message.role === 'user' ? (
                    <p className="whitespace-pre-wrap">{message.content}</p>
                  ) : (
                    <div className="prose prose-sm max-w-none prose-headings:text-sm prose-headings:font-semibold prose-p:my-1 prose-ul:my-1 prose-li:my-0">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {message.content}
                      </ReactMarkdown>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
          
          <p className="mt-3 text-xs text-gray-500 italic">
            Scroll to see older messages
          </p>
        </div>
      )}
    </div>
  );
}

// Follow-up Input Component
function FollowUpInput({ onSend, disabled }) {
  const [message, setMessage] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim()) {
      onSend(message);
      setMessage('');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex space-x-2">
      <input
        type="text"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder="Ask a follow-up question..."
        className="flex-1 px-4 py-2 border border-gray-300 rounded-md focus:ring-primary focus:border-primary"
        disabled={disabled}
      />
      <button
        type="submit"
        disabled={disabled || !message.trim()}
        className={`px-6 py-2 border border-transparent text-sm font-medium rounded-md text-white ${
          disabled || !message.trim()
            ? 'bg-gray-400 cursor-not-allowed'
            : 'bg-primary hover:bg-blue-700'
        } transition-colors`}
      >
        Send
      </button>
    </form>
  );
}

export default Analysis;
