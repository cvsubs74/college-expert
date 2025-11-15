import { useState, useEffect, useRef } from 'react';
import {
  PaperAirplaneIcon,
  SparklesIcon,
  UserIcon,
  AcademicCapIcon
} from '@heroicons/react/24/outline';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { startSession, sendMessage, extractFullResponse } from '../services/api';
import { useAuth } from '../context/AuthContext';

function Analysis() {
  const { currentUser } = useAuth();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [suggestedQuestions, setSuggestedQuestions] = useState([]);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Initial greeting with intelligent suggested questions
  useEffect(() => {
    if (messages.length === 0) {
      setSuggestedQuestions([
        "Analyze my chances at Stanford for Computer Science",
        "Compare my profile for MIT vs Caltech in Engineering",
        "What are my strengths and weaknesses for Ivy League schools?",
        "Help me build a balanced college list for Business majors"
      ]);
    }
  }, [messages.length]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');
    setLoading(true);

    // Add user message to chat
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);

    try {
      // Send message with user email tag
      const messageWithEmail = `[USER_EMAIL: ${currentUser?.email}] ${userMessage}`;
      const response = await startSession(messageWithEmail, currentUser?.email);

      // Extract response and suggested questions
      const { result, suggested_questions } = extractFullResponse(response);

      // Add assistant response
      setMessages(prev => [...prev, { role: 'assistant', content: result }]);

      // Update suggested questions
      if (suggested_questions && Array.isArray(suggested_questions) && suggested_questions.length > 0) {
        setSuggestedQuestions(suggested_questions);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry, I encountered an error. Please make sure you have uploaded your profile in the Student Profile tab and try again.'
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSuggestedQuestion = async (question) => {
    setInput(question);
    // Trigger send
    const event = { preventDefault: () => {} };
    setInput(question);
    setTimeout(() => {
      handleSendMessage(event);
    }, 100);
  };

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
        <div className="flex items-center space-x-3">
          <div className="p-3 bg-primary/10 rounded-lg">
            <AcademicCapIcon className="h-8 w-8 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">My College Strategy</h1>
            <p className="text-gray-600 mt-1">
              Get personalized admissions analysis and build your college list
            </p>
          </div>
        </div>
      </div>

      {/* Chat Container */}
      <div className="bg-white rounded-lg shadow-sm flex flex-col" style={{ height: 'calc(100vh - 280px)' }}>
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 && (
            <div className="text-center py-12">
              <SparklesIcon className="h-16 w-16 text-primary mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                Let's Build Your College Strategy
              </h2>
              <p className="text-gray-600 mb-6 max-w-2xl mx-auto">
                I'll help you analyze your admissions chances, compare universities, and build a balanced college list.
                Just tell me which colleges you're interested in and your intended major!
              </p>
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 max-w-2xl mx-auto text-left">
                <p className="text-sm text-blue-900 font-medium mb-2">💡 What I can help with:</p>
                <ul className="text-sm text-blue-800 space-y-1">
                  <li>• Analyze your chances at specific universities</li>
                  <li>• Compare multiple schools side-by-side</li>
                  <li>• Evaluate your profile strengths and weaknesses</li>
                  <li>• Build a balanced college list (reach, target, safety)</li>
                  <li>• Answer questions about your academic profile</li>
                </ul>
              </div>
            </div>
          )}

          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`flex space-x-3 max-w-3xl ${
                  message.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''
                }`}
              >
                <div
                  className={`flex-shrink-0 h-8 w-8 rounded-full flex items-center justify-center ${
                    message.role === 'user' ? 'bg-primary' : 'bg-gray-200'
                  }`}
                >
                  {message.role === 'user' ? (
                    <UserIcon className="h-5 w-5 text-white" />
                  ) : (
                    <AcademicCapIcon className="h-5 w-5 text-gray-600" />
                  )}
                </div>
                <div
                  className={`flex-1 rounded-lg p-4 ${
                    message.role === 'user'
                      ? 'bg-primary text-white'
                      : 'bg-gray-50 text-gray-900'
                  }`}
                >
                  {message.role === 'user' ? (
                    <p className="whitespace-pre-wrap">{message.content}</p>
                  ) : (
                    <div className="prose prose-sm max-w-none">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {message.content}
                      </ReactMarkdown>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="flex space-x-3 max-w-3xl">
                <div className="flex-shrink-0 h-8 w-8 rounded-full bg-gray-200 flex items-center justify-center">
                  <AcademicCapIcon className="h-5 w-5 text-gray-600" />
                </div>
                <div className="flex-1 rounded-lg p-4 bg-gray-50">
                  <div className="flex space-x-2">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Suggested Questions */}
        {suggestedQuestions.length > 0 && (
          <div className="border-t border-gray-200 p-4 bg-gray-50">
            <p className="text-sm font-medium text-gray-700 mb-3">💡 Suggested questions:</p>
            <div className="grid grid-cols-2 gap-2">
              {suggestedQuestions.slice(0, 4).map((question, index) => {
                // Color code buttons based on index
                const colorClasses = [
                  'bg-blue-50 border-blue-300 hover:bg-blue-100 hover:border-blue-400 text-blue-900',
                  'bg-green-50 border-green-300 hover:bg-green-100 hover:border-green-400 text-green-900',
                  'bg-purple-50 border-purple-300 hover:bg-purple-100 hover:border-purple-400 text-purple-900',
                  'bg-orange-50 border-orange-300 hover:bg-orange-100 hover:border-orange-400 text-orange-900'
                ];
                
                return (
                  <button
                    key={index}
                    onClick={() => handleSuggestedQuestion(question)}
                    disabled={loading}
                    className={`text-left text-sm px-4 py-2 border rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${colorClasses[index % 4]}`}
                  >
                    {question}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Input */}
        <div className="border-t border-gray-200 p-4">
          <form onSubmit={handleSendMessage} className="flex space-x-4">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about your chances, compare schools, or request analysis..."
              disabled={loading}
              className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="px-6 py-3 bg-primary text-white rounded-lg hover:bg-primary-dark transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
            >
              <PaperAirplaneIcon className="h-5 w-5" />
              <span>Send</span>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default Analysis;
